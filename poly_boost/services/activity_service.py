"""
Activity history service.

Provides functionality for querying user activity history on Polymarket.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import logging

from polymarket_apis.clients.data_client import PolymarketDataClient
from polymarket_apis.types.data_types import Activity

from poly_boost.core.wallet import Wallet
from poly_boost.core.wallet_manager import WalletManager


logger = logging.getLogger(__name__)


class ActivityService:
    """Service for querying user activity history."""

    def __init__(
        self,
        data_client: PolymarketDataClient,
        wallet_manager: Optional[WalletManager] = None
    ):
        """
        Initialize activity service.

        Args:
            data_client: Polymarket Data API client instance
            wallet_manager: WalletManager instance for resolving wallet identifiers
        """
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

    def get_activity(
        self,
        wallet: Union[Wallet, str],
        limit: int = 100,
        offset: int = 0,
        condition_id: Optional[Union[str, List[str]]] = None,
        activity_type: Optional[Union[str, List[str]]] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        side: Optional[str] = None,
        sort_by: str = "TIMESTAMP",
        sort_direction: str = "DESC"
    ) -> List[Activity]:
        """
        Get activity history for a wallet.

        Args:
            wallet: Wallet instance or wallet identifier (address/name)
            limit: Maximum number of activities to return (max 500)
            offset: Offset for pagination
            condition_id: Filter by condition ID(s)
            activity_type: Filter by activity type(s) - TRADE, SPLIT, MERGE, REDEEM, REWARD, CONVERSION
            start: Start timestamp for filtering
            end: End timestamp for filtering
            side: Filter by side (BUY or SELL)
            sort_by: Sort field - TIMESTAMP, TOKENS, CASH
            sort_direction: Sort direction - ASC or DESC

        Returns:
            List of Activity objects

        Raises:
            Exception: If API request fails
        """
        try:
            # Resolve wallet identifier to Wallet object
            wallet_obj = self._resolve_wallet(wallet)

            logger.info(
                f"Fetching activity for wallet: {wallet_obj.name} "
                f"(api_address={wallet_obj.api_address})"
            )

            # Get activity from data API using the api_address
            activities = self.data_client.get_activity(
                user=wallet_obj.api_address,
                limit=min(limit, 500),
                offset=offset,
                condition_id=condition_id,
                type=activity_type,
                start=start,
                end=end,
                side=side,
                sort_by=sort_by,
                sort_direction=sort_direction
            )

            logger.info(f"Found {len(activities)} activities for {wallet_obj.name}")
            return activities
        except Exception as e:
            logger.error(f"Failed to fetch activity: {e}")
            raise

    def get_activity_summary(
        self,
        wallet: Union[Wallet, str],
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get summarized activity information for a wallet.

        Args:
            wallet: Wallet instance or wallet identifier (address/name)
            limit: Maximum number of activities to return

        Returns:
            Summary dictionary with activity statistics
        """
        try:
            # Resolve wallet identifier to Wallet object
            wallet_obj = self._resolve_wallet(wallet)

            activities = self.get_activity(wallet_obj, limit=limit)

            # Calculate statistics
            activity_types = {}
            total_trades = 0
            total_volume = 0.0

            for activity in activities:
                # Count by type
                activity_types[activity.type] = activity_types.get(activity.type, 0) + 1

                # Calculate trade statistics
                if activity.type == "TRADE":
                    total_trades += 1
                    total_volume += activity.usdc_size

            return {
                "wallet_address": wallet_obj.api_address,
                "wallet_name": wallet_obj.name,
                "total_activities": len(activities),
                "activity_types": activity_types,
                "total_trades": total_trades,
                "total_volume": total_volume,
                "activities": [activity.model_dump() for activity in activities]
            }
        except Exception as e:
            logger.error(f"Failed to get activity summary: {e}")
            raise
