"""
Activity history endpoints.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query

from poly_boost.services.activity_service import ActivityService
from poly_boost.api.dependencies import get_activity_service


router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("/{wallet_address}")
async def get_activity(
    wallet_address: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of activities (1-500)"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    condition_id: Optional[str] = Query(None, description="Filter by condition ID"),
    activity_type: Optional[str] = Query(None, description="Filter by activity type (TRADE, SPLIT, MERGE, REDEEM, REWARD, CONVERSION)"),
    side: Optional[str] = Query(None, description="Filter by side (BUY or SELL)"),
    sort_by: str = Query("TIMESTAMP", description="Sort field (TIMESTAMP, TOKENS, CASH)"),
    sort_direction: str = Query("DESC", description="Sort direction (ASC or DESC)"),
    activity_service: ActivityService = Depends(get_activity_service)
) -> Dict[str, Any]:
    """
    Get activity history for a wallet.

    This endpoint returns user activity including trades, splits, merges, redemptions,
    rewards, and conversions from Polymarket.

    Args:
        wallet_address: Wallet address to query
        limit: Maximum number of activities to return (1-500, default 100)
        offset: Offset for pagination (default 0)
        condition_id: Filter by condition ID
        activity_type: Filter by activity type (TRADE, SPLIT, MERGE, REDEEM, REWARD, CONVERSION)
        side: Filter by side (BUY or SELL, only applies to TRADE activities)
        sort_by: Sort field - TIMESTAMP, TOKENS, CASH (default: TIMESTAMP)
        sort_direction: Sort direction - ASC or DESC (default: DESC)

    Returns:
        Activity summary including list of activities and statistics
    """
    try:
        summary = activity_service.get_activity_summary(
            wallet=wallet_address,
            limit=limit
        )
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{wallet_address}/list")
async def get_activity_list(
    wallet_address: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of activities (1-500)"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    condition_id: Optional[str] = Query(None, description="Filter by condition ID"),
    activity_type: Optional[str] = Query(None, description="Filter by activity type (TRADE, SPLIT, MERGE, REDEEM, REWARD, CONVERSION)"),
    side: Optional[str] = Query(None, description="Filter by side (BUY or SELL)"),
    sort_by: str = Query("TIMESTAMP", description="Sort field (TIMESTAMP, TOKENS, CASH)"),
    sort_direction: str = Query("DESC", description="Sort direction (ASC or DESC)"),
    activity_service: ActivityService = Depends(get_activity_service)
) -> List[Dict[str, Any]]:
    """
    Get activity list for a wallet (without summary statistics).

    This endpoint returns only the list of activities without aggregated statistics,
    suitable for direct consumption by frontend components.

    Args:
        wallet_address: Wallet address to query
        limit: Maximum number of activities to return (1-500, default 100)
        offset: Offset for pagination (default 0)
        condition_id: Filter by condition ID
        activity_type: Filter by activity type (TRADE, SPLIT, MERGE, REDEEM, REWARD, CONVERSION)
        side: Filter by side (BUY or SELL, only applies to TRADE activities)
        sort_by: Sort field - TIMESTAMP, TOKENS, CASH (default: TIMESTAMP)
        sort_direction: Sort direction - ASC or DESC (default: DESC)

    Returns:
        List of activity records
    """
    try:
        activities = activity_service.get_activity(
            wallet=wallet_address,
            limit=limit,
            offset=offset,
            condition_id=condition_id,
            activity_type=activity_type,
            side=side,
            sort_by=sort_by,
            sort_direction=sort_direction
        )

        # Convert to dict for JSON serialization
        return [activity.model_dump() for activity in activities]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
