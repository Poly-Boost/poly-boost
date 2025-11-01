"""Tests for SelfRedeemMonitor core logic."""

import sys
import time
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from poly_boost.core.self_redeem_monitor import RedeemTask, SelfRedeemMonitor


class FakeWallet:
    def __init__(self, name: str, api_address: str, eoa_address: str, signature_type: int = 0):
        self.name = name
        self.api_address = api_address
        self.eoa_address = eoa_address
        self.signature_type = signature_type
        self.requires_private_key = True


class FakeWalletManager:
    def __init__(self, wallets):
        self._wallets = wallets

    def list_tradable(self):
        return [w for w in self._wallets if getattr(w, "requires_private_key", False)]


class FakePosition:
    def __init__(
        self,
        condition_id: str,
        token_id: str,
        opposite_asset: str,
        size: float,
        outcome_index: int,
        redeemable: bool = True,
    ):
        self.condition_id = condition_id
        self.conditionId = condition_id
        self.token_id = token_id
        self.tokenId = token_id
        self.opposite_asset = opposite_asset
        self.oppositeAsset = opposite_asset
        self.size = size
        self.outcome_index = outcome_index
        self.outcomeIndex = outcome_index
        self.redeemable = redeemable


class FakePositionService:
    def __init__(self, positions=None):
        self.positions = positions or []
        self.calls = []

    def get_positions(self, wallet):
        self.calls.append(wallet)
        return list(self.positions)


class FakeOrderService:
    def __init__(self):
        self.calls = []

    def claim_rewards(self, condition_id, amounts, token_ids):
        self.calls.append(
            {"condition_id": condition_id, "amounts": list(amounts), "token_ids": token_ids}
        )


class FakeOrderServiceFactory:
    def __init__(self):
        self.created_for = {}

    def __call__(self, wallet):
        if wallet.name not in self.created_for:
            self.created_for[wallet.name] = FakeOrderService()
        return self.created_for[wallet.name]


class SelfRedeemMonitorTests(unittest.TestCase):
    def setUp(self):
        self.wallet = FakeWallet(
            name="TraderOne",
            api_address="0xabc1230000000000000000000000000000000000",
            eoa_address="0xabc1230000000000000000000000000000000000",
        )
        self.wallet_manager = FakeWalletManager([self.wallet])

    def _build_monitor(self, position_service, factory, extra_cfg=None):
        cfg = {
            "auto_redeem": {
                "enabled": True,
                "poll_interval_seconds": 1,
                "cool_down_seconds": 3,
                "dry_run": False,
            }
        }
        if extra_cfg:
            cfg["auto_redeem"].update(extra_cfg)
        return SelfRedeemMonitor(
            wallet_manager=self.wallet_manager,
            position_svc=position_service,
            order_svc_factory=factory,
            cfg=cfg,
        )

    def test_collect_tasks_groups_outcomes(self):
        positions = [
            FakePosition(
                condition_id="0xcond1",
                token_id="token_yes",
                opposite_asset="token_no",
                size=10,
                outcome_index=0,
            ),
            FakePosition(
                condition_id="0xcond1",
                token_id="token_no",
                opposite_asset="token_yes",
                size=5,
                outcome_index=1,
            ),
            FakePosition(
                condition_id="0xcond2",
                token_id="token_yes_2",
                opposite_asset="token_no_2",
                size=7,
                outcome_index=0,
            ),
            FakePosition(
                condition_id="0xcond3",
                token_id="token_skip",
                opposite_asset="token_skip_opposite",
                size=3,
                outcome_index=0,
                redeemable=False,
            ),
        ]
        position_service = FakePositionService(positions)
        factory = FakeOrderServiceFactory()
        monitor = self._build_monitor(position_service, factory)

        tasks = monitor._collect_tasks(self.wallet)

        self.assertEqual(2, len(tasks))
        task_map = {task.condition_id: task for task in tasks}

        self.assertIn("0xcond1", task_map)
        cond1 = task_map["0xcond1"]
        self.assertEqual([10.0, 5.0], cond1.amounts)
        self.assertEqual(["token_yes", "token_no"], cond1.token_ids)

        self.assertIn("0xcond2", task_map)
        cond2 = task_map["0xcond2"]
        self.assertEqual([7.0, 0.0], cond2.amounts)
        self.assertEqual(["token_yes_2", "token_no_2"], cond2.token_ids)

    def test_process_task_dry_run_skips_order_service(self):
        position_service = FakePositionService([])
        factory = FakeOrderServiceFactory()
        monitor = self._build_monitor(
            position_service,
            factory,
            extra_cfg={"dry_run": True, "cool_down_seconds": 5},
        )

        task = RedeemTask(
            condition_id="0xcond_dry_run",
            amounts=[2.0, 0.0],
            token_ids=["token_yes", None],
        )

        monitor._process_task(self.wallet, task)
        # Dry-run should not call claim_rewards but should set cooldown.
        service = factory.created_for.get(self.wallet.name)
        self.assertTrue(service is None or len(service.calls) == 0)
        self.assertIn(
            (self.wallet.api_address.lower(), task.condition_id.lower()),
            monitor._cooldowns,
        )

    def test_process_task_respects_cooldown_and_allows_retry_after_expiry(self):
        position_service = FakePositionService([])
        factory = FakeOrderServiceFactory()
        monitor = self._build_monitor(
            position_service,
            factory,
            extra_cfg={"dry_run": False, "cool_down_seconds": 60},
        )

        task = RedeemTask(
            condition_id="0xcond_retry",
            amounts=[1.0, 0.5],
            token_ids=["token_yes_retry", "token_no_retry"],
        )

        monitor._process_task(self.wallet, task)
        service = factory.created_for[self.wallet.name]
        self.assertEqual(1, len(service.calls))

        # Second call should be skipped due to cooldown.
        monitor._process_task(self.wallet, task)
        self.assertEqual(1, len(service.calls))

        # Force cooldown expiry and retry.
        key = (self.wallet.api_address.lower(), task.condition_id.lower())
        monitor._cooldowns[key] = time.monotonic() - 1
        monitor._process_task(self.wallet, task)
        self.assertEqual(2, len(service.calls))


if __name__ == "__main__":
    unittest.main()
