"""
Copy trading control endpoints.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from poly_boost.services.trading_service import TradingService
from poly_boost.api.dependencies import get_trading_service


router = APIRouter(prefix="/trading", tags=["trading"])


class StartCopyTradingRequest(BaseModel):
    """Request model for starting copy trading."""
    trader_name: str
    source_wallet: str


class StopCopyTradingRequest(BaseModel):
    """Request model for stopping copy trading."""
    trader_name: str
    source_wallet: str


@router.post("/copy/start")
async def start_copy_trading(
    request: StartCopyTradingRequest,
    trading_service: TradingService = Depends(get_trading_service)
) -> Dict[str, Any]:
    """
    Start copy trading for a specific source wallet.

    Args:
        request: Start copy trading request

    Returns:
        Status information
    """
    try:
        result = trading_service.start_copy_trading(
            request.trader_name,
            request.source_wallet
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/copy/stop")
async def stop_copy_trading(
    request: StopCopyTradingRequest,
    trading_service: TradingService = Depends(get_trading_service)
) -> Dict[str, Any]:
    """
    Stop copy trading for a specific source wallet.

    Args:
        request: Stop copy trading request

    Returns:
        Status information
    """
    try:
        result = trading_service.stop_copy_trading(
            request.trader_name,
            request.source_wallet
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_copy_trading_status(
    trading_service: TradingService = Depends(get_trading_service)
) -> Dict[str, Any]:
    """
    Get status of all copy trading operations.

    Returns:
        Copy trading status information
    """
    try:
        status = trading_service.get_copy_trading_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traders")
async def list_traders(
    trading_service: TradingService = Depends(get_trading_service)
) -> List[str]:
    """
    List all registered copy traders.

    Returns:
        List of trader names
    """
    try:
        traders = trading_service.list_traders()
        return traders
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traders/{trader_name}/stats")
async def get_trader_stats(
    trader_name: str,
    trading_service: TradingService = Depends(get_trading_service)
) -> Dict[str, Any]:
    """
    Get statistics for a specific trader.

    Args:
        trader_name: Name of the copy trader

    Returns:
        Trader statistics
    """
    try:
        stats = trading_service.get_trader_stats(trader_name)
        return stats
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
