"""
Configuration endpoints.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException

from poly_boost.api.dependencies import get_config


router = APIRouter(prefix="/config", tags=["config"])


@router.get("/wallets")
async def get_configured_wallets(
    config: dict = Depends(get_config)
) -> List[Dict[str, Any]]:
    """
    Get list of monitored wallets from configuration.

    Returns:
        List of wallet configurations
    """
    try:
        monitoring_config = config.get('monitoring', {})
        monitored_wallets = monitoring_config.get('wallets', [])

        # Get user wallets config
        user_wallets = config.get('user_wallets', [])

        result = []

        # Add monitored wallets (source wallets being tracked)
        for wallet in monitored_wallets:
            result.append({
                'address': wallet,
                'type': 'monitored',
                'name': f'Monitored-{wallet[:8]}'
            })

        # Add user wallets (copy trading wallets)
        for wallet_config in user_wallets:
            result.append({
                'address': wallet_config.get('address'),
                'proxy_address': wallet_config.get('proxy_address'),
                'type': 'user',
                'name': wallet_config.get('name', 'Unknown')
            })

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
