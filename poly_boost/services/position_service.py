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


logger = logging.getLogger(__name__)


class PositionService:
    """Service for managing and querying positions."""

    def __init__(self, clob_client: ClobClient, data_client: PolymarketDataClient):
        """
        Initialize position service.

        Args:
            clob_client: Polymarket CLOB client instance
            data_client: Polymarket Data API client instance
        """
        self.clob_client = clob_client
        self.data_client = data_client

    def get_positions(self, wallet: Union[Wallet, str]) -> List[Position]:
        """
        Get all positions for a wallet.

        Args:
            wallet: Wallet instance or wallet address string

        Returns:
            List of Position objects

        Raises:
            Exception: If API request fails
        """
        try:
            # Support both Wallet objects and address strings for backward compatibility
            if isinstance(wallet, Wallet):
                address = wallet.api_address
                wallet_name = wallet.name
            else:
                address = wallet
                wallet_name = address

            logger.info(f"Fetching positions for wallet: {wallet_name} ({address})")

            # Get positions from data API using the correct address
            positions = self.data_client.get_positions(user=address)

            logger.info(f"Found {len(positions)} positions for {wallet_name}")
            return positions
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            raise

    def get_position_value(self, wallet: Union[Wallet, str]) -> Decimal:
        """
        Calculate total position value for a wallet.

        Args:
            wallet: Wallet instance or wallet address string

        Returns:
            Total position value in USDC

        Raises:
            Exception: If calculation fails
        """
        try:
            # Support both Wallet objects and address strings
            if isinstance(wallet, Wallet):
                address = wallet.api_address
                wallet_name = wallet.name
            else:
                address = wallet
                wallet_name = address

            # Call API directly to avoid Pydantic validation issues
            params = {"user": address}
            response = self.data_client.client.get(
                self.data_client._build_url("/value"),
                params=params
            )
            response.raise_for_status()
            data = response.json()[0]

            total_value = Decimal(str(data.get("value", 0)))

            logger.info(f"Total position value for {wallet_name}: {total_value}")
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
            wallet: Wallet instance or wallet address string

        Returns:
            Summary dictionary with position statistics
        """
        try:
            # Support both Wallet objects and address strings
            if isinstance(wallet, Wallet):
                address = wallet.api_address
                wallet_name = wallet.name
            else:
                address = wallet
                wallet_name = address

            positions = self.get_positions(wallet)
            total_value = self.get_position_value(wallet)

            return {
                "wallet_address": address,
                "wallet_name": wallet_name,
                "total_positions": len(positions),
                "total_value": float(total_value),
                "positions": positions
            }
        except Exception as e:
            logger.error(f"Failed to get position summary: {e}")
            raise
