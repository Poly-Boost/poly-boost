"""
Position management service.

Provides functionality for querying and managing wallet positions on Polymarket.
"""

from typing import List, Optional, Dict, Any, Union
from decimal import Decimal
import logging

from py_clob_client.client import ClobClient
from polymarket_apis.clients.data_client import PolymarketDataClient
from polymarket_apis.types.data_types import Position

from poly_boost.core.wallet import Wallet
from poly_boost.core.wallet_manager import WalletManager


logger = logging.getLogger(__name__)


class PositionService:
    """Service for managing and querying positions."""

    def __init__(
        self,
        clob_client: ClobClient,
        data_client: PolymarketDataClient,
        wallet_manager: Optional[WalletManager] = None
    ):
        """
        Initialize position service.

        Args:
            clob_client: Polymarket CLOB client instance
            data_client: Polymarket Data API client instance
            wallet_manager: WalletManager instance for resolving wallet identifiers
        """
        self.clob_client = clob_client
        self.data_client = data_client
        self.wallet_manager = wallet_manager

    def _resolve_wallet(self, wallet: Union[Wallet, str]) -> Wallet:
        """
        Resolve wallet identifier to Wallet object.

        Args:
            wallet: Wallet instance or wallet identifier (address/name)

        Returns:
            Wallet instance

        Raises:
            ValueError: If wallet_manager not set and str provided
            ValueError: If wallet identifier not found
        """
        if isinstance(wallet, Wallet):
            return wallet

        # wallet is a string identifier
        if self.wallet_manager is None:
            raise ValueError(
                "WalletManager not configured. Cannot resolve wallet identifier. "
                "Please pass a Wallet object instead of a string."
            )

        resolved = self.wallet_manager.get_or_raise(wallet)
        logger.debug(
            f"Resolved wallet identifier '{wallet}' to wallet '{resolved.name}' "
            f"(api_address={resolved.api_address})"
        )
        return resolved

    def get_positions(self, wallet: Union[Wallet, str]) -> List[Position]:
        """
        Get all positions for a wallet.

        Args:
            wallet: Wallet instance or wallet identifier (address/name)

        Returns:
            List of Position objects

        Raises:
            Exception: If API request fails
        """
        try:
            # Resolve wallet identifier to Wallet object
            wallet_obj = self._resolve_wallet(wallet)

            logger.info(
                f"Fetching positions for wallet: {wallet_obj.name} "
                f"(api_address={wallet_obj.api_address})"
            )

            # Get positions from data API using the CORRECT address (api_address)
            positions = self.data_client.get_positions(user=wallet_obj.api_address, redeemable=None)

            logger.info(f"Found {len(positions)} positions for {wallet_obj.name}")
            return positions
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            raise

    def get_position_value(self, wallet: Union[Wallet, str]) -> Decimal:
        """
        Calculate total position value for a wallet.

        Args:
            wallet: Wallet instance or wallet identifier (address/name)

        Returns:
            Total position value in USDC

        Raises:
            Exception: If calculation fails
        """
        try:
            # Resolve wallet identifier to Wallet object
            wallet_obj = self._resolve_wallet(wallet)

            # Call API directly to avoid Pydantic validation issues
            # Use wallet.api_address - the correct address based on wallet type
            params = {"user": wallet_obj.api_address}
            response = self.data_client.client.get(
                self.data_client._build_url("/value"),
                params=params
            )
            response.raise_for_status()
            data = response.json()[0]

            total_value = Decimal(str(data.get("value", 0)))

            logger.info(f"Total position value for {wallet_obj.name}: {total_value}")
            return total_value
        except Exception as e:
            logger.error(f"Failed to calculate position value: {e}")
            raise

    def close_position(
        self,
        wallet_address: str,
        market_id: str,
        outcome: str,
        amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Close a position (sell shares).

        Args:
            wallet_address: Wallet address
            market_id: Market/condition ID
            outcome: Outcome to sell (YES/NO)
            amount: Amount to sell (None = all)

        Returns:
            Transaction result dictionary

        Raises:
            Exception: If transaction fails
        """
        try:
            # TODO: Implement position closing logic
            logger.info(
                f"Closing position for {wallet_address}: "
                f"market={market_id}, outcome={outcome}, amount={amount}"
            )

            # Placeholder
            return {"status": "pending"}
        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            raise

    def get_position_summary(self, wallet: Union[Wallet, str]) -> Dict[str, Any]:
        """
        Get summarized position information for a wallet.

        Args:
            wallet: Wallet instance or wallet identifier (address/name)

        Returns:
            Summary dictionary with position statistics
        """
        try:
            # Resolve wallet identifier to Wallet object
            wallet_obj = self._resolve_wallet(wallet)

            positions = self.get_positions(wallet_obj)
            total_value = self.get_position_value(wallet_obj)

            return {
                "wallet_address": wallet_obj.api_address,
                "wallet_name": wallet_obj.name,
                "total_positions": len(positions),
                "total_value": float(total_value),
                "positions": positions
            }
        except Exception as e:
            logger.error(f"Failed to get position summary: {e}")
            raise
