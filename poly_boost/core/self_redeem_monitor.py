"""
Automatic self-redeem monitor.

Polls configured tradable wallets, looks for redeemable positions, and
invokes the order service to claim rewards. Designed to run alongside
existing monitoring/copy-trading loops without blocking them.
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional, Tuple

if TYPE_CHECKING:
    from poly_boost.core.wallet import Wallet
    from poly_boost.core.wallet_manager import WalletManager
    from poly_boost.services.order_service import OrderService
    from poly_boost.services.position_service import PositionService
else:
    Wallet = Any
    WalletManager = Any

logger = logging.getLogger(__name__)


@dataclass
class RedeemTask:
    """Lightweight container for a single redeem attempt."""

    condition_id: str
    token_id: str
    amount: float


class SelfRedeemMonitor:
    """
    Background monitor that automatically redeems resolved positions.

    Key features:
    - Per-wallet polling with configurable interval
    - Optional include/exclude lists for wallets
    - Cooldown-based deduplication to prevent duplicate redeems
    - Dry-run mode for validation without sending transactions
    """

    def __init__(
        self,
        wallet_manager: WalletManager,
        position_svc: "PositionService",
        order_svc_factory: Callable[[Wallet], "OrderService"],
        cfg: Optional[dict] = None,
    ) -> None:
        self.wallet_manager = wallet_manager
        self.position_svc = position_svc
        self.order_svc_factory = order_svc_factory

        # Accept either the global config or an auto_redeem section directly.
        cfg = cfg or {}
        self.config = cfg.get("auto_redeem", cfg)

        self.enabled = bool(self.config.get("enabled", True))
        self.poll_interval = max(int(self.config.get("poll_interval_seconds", 60)), 1)
        self.cool_down = max(int(self.config.get("cool_down_seconds", 600)), 1)
        self.max_parallel = max(int(self.config.get("max_parallel_redeems", 3)), 1)
        self.dry_run = bool(self.config.get("dry_run", False))

        include = self.config.get("include_wallets") or []
        exclude = self.config.get("exclude_wallets") or []
        self.include_filters = {self._normalize_identifier(v) for v in include}
        self.exclude_filters = {self._normalize_identifier(v) for v in exclude}

        self._stop_event = threading.Event()
        self._executor: Optional[ThreadPoolExecutor] = None
        self._started = False

        # Cooldown tracking to prevent duplicate redeems.
        self._cooldowns: Dict[Tuple[str, str], float] = {}
        self._cooldown_lock = threading.Lock()

        # Cache order services per wallet to avoid repeated client construction.
        self._order_service_cache: Dict[str, "OrderService"] = {}
        self._order_service_lock = threading.Lock()

    @staticmethod
    def _normalize_identifier(value: str) -> str:
        return value.lower().strip()

    def start(self) -> None:
        """Start monitoring in background threads."""
        if not self.enabled:
            logger.info("Auto redeem disabled; SelfRedeemMonitor not started")
            return

        if self._started:
            logger.warning("SelfRedeemMonitor already running; start() ignored")
            return

        wallets = list(self._iter_eligible_wallets())
        if not wallets:
            logger.info("SelfRedeemMonitor found no eligible tradable wallets")
            return

        max_workers = min(self.max_parallel, len(wallets))
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="self-redeem",
        )
        self._stop_event.clear()
        self._started = True

        for wallet in wallets:
            self._executor.submit(self._wallet_loop, wallet)

        logger.info(
            "SelfRedeemMonitor started for %d wallet(s) (interval=%ss, cooldown=%ss, dry_run=%s)",
            len(wallets),
            self.poll_interval,
            self.cool_down,
            self.dry_run,
        )

    def stop(self) -> None:
        """Signal all threads to stop and wait for completion."""
        if not self._started:
            return

        self._stop_event.set()

        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

        self._started = False
        logger.info("SelfRedeemMonitor stopped")

    def _iter_eligible_wallets(self) -> Iterable[Wallet]:
        for wallet in self.wallet_manager.list_tradable():
            if self._wallet_included(wallet):
                yield wallet
            else:
                logger.debug(
                    "Skipping wallet '%s' for auto redeem (filtered by config)",
                    wallet.name,
                )

    def _wallet_included(self, wallet: Wallet) -> bool:
        def matches(identifier: str) -> bool:
            return identifier in {
                wallet.name.lower(),
                wallet.api_address.lower(),
                wallet.eoa_address.lower(),
            }

        if self.include_filters and not any(
            matches(identifier) for identifier in self.include_filters
        ):
            return False

        if any(matches(identifier) for identifier in self.exclude_filters):
            return False

        return True

    def _wallet_loop(self, wallet: Wallet) -> None:
        logger.info(
            "Auto redeem loop started for wallet '%s' (api=%s, signature_type=%s)",
            wallet.name,
            wallet.api_address,
            wallet.signature_type,
        )

        while not self._stop_event.is_set():
            loop_started_at = time.monotonic()
            try:
                tasks = self._collect_tasks(wallet)
                if tasks:
                    logger.info(
                        "Wallet '%s': %d redeemable condition(s) detected",
                        wallet.name,
                        len(tasks),
                    )
                for task in tasks:
                    if self._stop_event.is_set():
                        break
                    self._process_task(wallet, task)
            except Exception as exc:
                logger.error(
                    "Wallet '%s' auto redeem tick failed: %s",
                    wallet.name,
                    exc,
                    exc_info=True,
                )

            # Wait for the next poll while still allowing fast shutdown.
            elapsed = time.monotonic() - loop_started_at
            remaining = max(self.poll_interval - elapsed, 0)
            if remaining > 0:
                self._stop_event.wait(remaining)

        logger.info("Auto redeem loop exited for wallet '%s'", wallet.name)

    def _collect_tasks(self, wallet: Wallet) -> List[RedeemTask]:
        positions = self.position_svc.get_positions(wallet)
        redeemables: Dict[str, RedeemTask] = {}

        for position in positions:
            if not getattr(position, "redeemable", False):
                continue

            condition_id = self._extract_attr(position, "condition_id", "conditionId")
            if not condition_id:
                logger.debug(
                    "Wallet '%s': redeemable position missing condition_id; skipping",
                    wallet.name,
                )
                continue

            size = float(getattr(position, "size", 0.0) or 0.0)
            if size <= 0:
                logger.debug(
                    "Wallet '%s': condition %s has non-positive size; skipping",
                    wallet.name,
                    condition_id,
                )
                continue

            token_id = self._extract_attr(position, "token_id", "tokenId")
            if not token_id:
                token_id = self._extract_attr(position, "asset", "asset")

            if not token_id:
                logger.debug(
                    "Wallet '%s': condition %s missing token_id; skipping position",
                    wallet.name,
                    condition_id,
                )
                continue

            existing = redeemables.get(condition_id)
            if not existing or size > existing.amount:
                redeemables[condition_id] = RedeemTask(
                    condition_id=condition_id,
                    token_id=token_id,
                    amount=size,
                )

        return list(redeemables.values())

    @staticmethod
    def _extract_attr(
        position: object,
        primary: str,
        fallback: str,
        default: Optional[int | str] = None,
    ):
        value = getattr(position, primary, None)
        if value is None:
            value = getattr(position, fallback, default)
        return value if value is not None else default

    def _process_task(self, wallet: Wallet, task: RedeemTask) -> None:
        cooldown_key = (
            wallet.api_address.lower(),
            task.condition_id.lower(),
        )

        if self._is_in_cooldown(cooldown_key):
            logger.debug(
                "Wallet '%s': skipping condition %s due to cooldown",
                wallet.name,
                task.condition_id,
            )
            return

        logger.info(
            "Wallet '%s': attempting auto redeem for condition %s (token_id=%s, amount=%s)",
            wallet.name,
            task.condition_id,
            task.token_id,
            task.amount,
        )

        if self.dry_run:
            logger.info(
                "Wallet '%s': [dry-run] would call claim_rewards(condition_id=%s, token_id=%s, amount=%s)",
                wallet.name,
                task.condition_id,
                task.token_id,
                task.amount,
            )
            self._mark_cooldown(cooldown_key)
            return

        try:
            order_service = self._get_order_service(wallet)
            order_service.claim_rewards(
                condition_id=task.condition_id,
                token_id=task.token_id,
                amount=task.amount,
            )
            logger.info(
                "Wallet '%s': auto redeem succeeded for condition %s",
                wallet.name,
                task.condition_id,
            )
            self._mark_cooldown(cooldown_key)
        except Exception as exc:
            logger.error(
                "Wallet '%s': auto redeem failed for condition %s: %s",
                wallet.name,
                task.condition_id,
                exc,
                exc_info=True,
            )
            self._mark_cooldown(cooldown_key)

    def _is_in_cooldown(self, key: Tuple[str, str]) -> bool:
        now = time.monotonic()
        with self._cooldown_lock:
            expires = self._cooldowns.get(key)
            if expires and expires > now:
                return True
            if expires and expires <= now:
                del self._cooldowns[key]
            return False

    def _mark_cooldown(self, key: Tuple[str, str]) -> None:
        expires = time.monotonic() + self.cool_down
        with self._cooldown_lock:
            self._cooldowns[key] = expires

    def _get_order_service(self, wallet: Wallet) -> "OrderService":
        key = wallet.api_address.lower()
        with self._order_service_lock:
            if key not in self._order_service_cache:
                self._order_service_cache[key] = self.order_svc_factory(wallet)
            return self._order_service_cache[key]
