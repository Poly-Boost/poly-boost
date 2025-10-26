"""
Wallet management endpoints.
"""

from typing import Dict, Any, List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException

from poly_boost.services.wallet_service import WalletService
from poly_boost.api.dependencies import get_wallet_service


router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.get("/{wallet_address}")
async def get_wallet_info(
    wallet_address: str,
    wallet_service: WalletService = Depends(get_wallet_service)
) -> Dict[str, Any]:
    """
    Get information about a wallet.

    Args:
        wallet_address: Wallet address

    Returns:
        Wallet information
    """
    try:
        info = wallet_service.get_wallet_info(wallet_address)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{wallet_address}/balance")
async def get_wallet_balance(
    wallet_address: str,
    wallet_service: WalletService = Depends(get_wallet_service)
) -> Dict[str, Any]:
    """
    Get USDC balance for a wallet.

    Args:
        wallet_address: Wallet address

    Returns:
        Balance information (returns null balance on error instead of throwing)
    """
    try:
        balance = wallet_service.get_balance(wallet_address)
        return {
            "wallet_address": wallet_address,
            "balance": float(balance),
            "success": True,
            "error": None
        }
    except Exception as e:
        # Log error but return success response with null balance
        # This ensures position list is not affected by balance query failures
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to fetch balance for {wallet_address}: {e}")

        return {
            "wallet_address": wallet_address,
            "balance": None,
            "success": False,
            "error": str(e)
        }


@router.get("/")
async def list_managed_wallets(
    wallet_service: WalletService = Depends(get_wallet_service)
) -> List[Dict[str, Any]]:
    """
    List all managed wallets.

    Returns:
        List of managed wallet information
    """
    try:
        wallets = wallet_service.list_managed_wallets()
        return wallets
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
