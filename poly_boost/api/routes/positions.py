"""
Position management endpoints.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException

from poly_boost.services.position_service import PositionService
from poly_boost.api.dependencies import get_position_service


router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("/{wallet_address}")
async def get_positions(
    wallet_address: str,
    position_service: PositionService = Depends(get_position_service)
) -> Dict[str, Any]:
    """
    Get all positions for a wallet.

    Args:
        wallet_address: Wallet address to query

    Returns:
        Position summary including list of positions and total value
    """
    try:
        summary = position_service.get_position_summary(wallet_address)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{wallet_address}/value")
async def get_position_value(
    wallet_address: str,
    position_service: PositionService = Depends(get_position_service)
) -> Dict[str, Any]:
    """
    Get total position value for a wallet.

    Args:
        wallet_address: Wallet address

    Returns:
        Total position value in USDC
    """
    try:
        value = position_service.get_position_value(wallet_address)
        return {
            "wallet_address": wallet_address,
            "total_value": float(value)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{wallet_address}/close")
async def close_position(
    wallet_address: str,
    market_id: str,
    outcome: str,
    amount: float = None,
    position_service: PositionService = Depends(get_position_service)
) -> Dict[str, Any]:
    """
    Close a position (sell shares).

    Args:
        wallet_address: Wallet address
        market_id: Market/condition ID
        outcome: Outcome to sell (YES/NO)
        amount: Amount to sell (None = all)

    Returns:
        Transaction result
    """
    try:
        from decimal import Decimal

        amount_decimal = Decimal(str(amount)) if amount else None
        result = position_service.close_position(
            wallet_address, market_id, outcome, amount_decimal
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
