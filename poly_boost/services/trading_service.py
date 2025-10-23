"""
Trading control service.

Manages copy trading operations, including starting/stopping copy traders
and monitoring their status.
"""

from typing import Dict, List, Optional, Any, Union
import logging
from threading import Lock

from poly_boost.core.wallet_monitor import WalletMonitor
from poly_boost.core.activity_queue import ActivityQueue
from poly_boost.core.copy_trader import CopyTrader
from poly_boost.core.wallet import Wallet, ProxyWallet


logger = logging.getLogger(__name__)


class TradingService:
    """Service for controlling copy trading operations."""

    def __init__(
        self,
        activity_queue: ActivityQueue,
        wallet_monitor: Optional[WalletMonitor] = None
    ):
        """
        Initialize trading service.

        Args:
            activity_queue: Activity queue instance for pub/sub
            wallet_monitor: Optional existing wallet monitor instance
        """
        self.activity_queue = activity_queue
        self.wallet_monitor = wallet_monitor
        self.copy_traders: Dict[str, CopyTrader] = {}  # wallet_name -> CopyTrader
        self.active_subscriptions: Dict[str, List[str]] = {}  # source_wallet -> [trader_names]
        self._lock = Lock()

        logger.info("TradingService initialized")

    def add_copy_trader(
        self,
        wallet_config: Union[Wallet, dict],
        polygon_rpc_config: dict,
        verify_ssl: bool = True
    ) -> str:
        """
        Register a new copy trader.

        Args:
            wallet_config: Wallet instance or wallet configuration dictionary
            polygon_rpc_config: Polygon RPC configuration
            verify_ssl: Whether to verify SSL certificates

        Returns:
            Trader name/ID

        Raises:
            ValueError: If trader already exists or configuration is invalid
        """
        # Convert Wallet object to dict if needed (for backward compatibility with CopyTrader)
        if isinstance(wallet_config, Wallet):
            wallet = wallet_config
            wallet_name = wallet.name

            # Convert Wallet to dict format expected by CopyTrader
            wallet_dict = {
                "name": wallet.name,
                "address": wallet.eoa_address,
                "signature_type": wallet.signature_type
            }

            # Add proxy_address if it's a proxy wallet
            if isinstance(wallet, ProxyWallet):
                wallet_dict["proxy_address"] = wallet.proxy_address

            # Add private_key_env (CopyTrader needs this to load private key)
            # Note: This is a workaround; ideally CopyTrader should accept Wallet objects
            if wallet.requires_private_key:
                # We need to extract the private_key_env from the Wallet
                # For now, we'll need to pass it via the Wallet's internal attribute
                if hasattr(wallet, '_private_key_env'):
                    wallet_dict["private_key_env"] = wallet._private_key_env

            wallet_config = wallet_dict
        else:
            wallet_name = wallet_config.get("name")
            if not wallet_name:
                raise ValueError("Wallet configuration must include 'name' field")

        with self._lock:
            if wallet_name in self.copy_traders:
                raise ValueError(f"Copy trader '{wallet_name}' already exists")

            try:
                trader = CopyTrader(
                    wallet_config=wallet_config,
                    activity_queue=self.activity_queue,
                    polygon_rpc_config=polygon_rpc_config,
                    verify_ssl=verify_ssl
                )
                self.copy_traders[wallet_name] = trader
                logger.info(f"Copy trader '{wallet_name}' registered")
                return wallet_name
            except Exception as e:
                logger.error(f"Failed to create copy trader '{wallet_name}': {e}")
                raise

    def start_copy_trading(self, trader_name: str, source_wallet: str) -> Dict[str, Any]:
        """
        Start copy trading for a specific source wallet.

        Args:
            trader_name: Name of the copy trader
            source_wallet: Source wallet address to copy from

        Returns:
            Status dictionary

        Raises:
            ValueError: If trader not found
        """
        with self._lock:
            if trader_name not in self.copy_traders:
                raise ValueError(f"Copy trader '{trader_name}' not found")

            trader = self.copy_traders[trader_name]

            try:
                # Start copy trading (subscribes to activity queue)
                trader.run(source_wallet)

                # Track subscription
                if source_wallet not in self.active_subscriptions:
                    self.active_subscriptions[source_wallet] = []
                self.active_subscriptions[source_wallet].append(trader_name)

                logger.info(
                    f"Copy trading started: trader='{trader_name}', "
                    f"source='{source_wallet}'"
                )

                return {
                    "status": "started",
                    "trader": trader_name,
                    "source_wallet": source_wallet
                }
            except Exception as e:
                logger.error(f"Failed to start copy trading: {e}")
                raise

    def stop_copy_trading(self, trader_name: str, source_wallet: str) -> Dict[str, Any]:
        """
        Stop copy trading for a specific source wallet.

        Args:
            trader_name: Name of the copy trader
            source_wallet: Source wallet address

        Returns:
            Status dictionary

        Raises:
            ValueError: If trader not found or not subscribed
        """
        with self._lock:
            if trader_name not in self.copy_traders:
                raise ValueError(f"Copy trader '{trader_name}' not found")

            # TODO: Implement unsubscribe logic in CopyTrader
            # For now, just remove from tracking

            if source_wallet in self.active_subscriptions:
                if trader_name in self.active_subscriptions[source_wallet]:
                    self.active_subscriptions[source_wallet].remove(trader_name)

                    if not self.active_subscriptions[source_wallet]:
                        del self.active_subscriptions[source_wallet]

            logger.info(
                f"Copy trading stopped: trader='{trader_name}', "
                f"source='{source_wallet}'"
            )

            return {
                "status": "stopped",
                "trader": trader_name,
                "source_wallet": source_wallet
            }

    def get_copy_trading_status(self) -> Dict[str, Any]:
        """
        Get status of all copy trading operations.

        Returns:
            Dictionary with copy trading status information
        """
        with self._lock:
            traders_info = []

            for trader_name, trader in self.copy_traders.items():
                # Get trader statistics
                stats = trader.get_stats()

                traders_info.append({
                    "name": trader_name,
                    "wallet_address": trader.wallet_config.get("address"),
                    "stats": stats
                })

            return {
                "total_traders": len(self.copy_traders),
                "active_subscriptions": dict(self.active_subscriptions),
                "traders": traders_info
            }

    def get_trader_stats(self, trader_name: str) -> Dict[str, Any]:
        """
        Get statistics for a specific trader.

        Args:
            trader_name: Name of the copy trader

        Returns:
            Statistics dictionary

        Raises:
            ValueError: If trader not found
        """
        with self._lock:
            if trader_name not in self.copy_traders:
                raise ValueError(f"Copy trader '{trader_name}' not found")

            trader = self.copy_traders[trader_name]
            return trader.get_stats()

    def list_traders(self) -> List[str]:
        """
        List all registered copy traders.

        Returns:
            List of trader names
        """
        with self._lock:
            return list(self.copy_traders.keys())
