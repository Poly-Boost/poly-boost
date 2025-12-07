"""
Order management endpoints.
"""

from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException
from polymarket_apis.types.clob_types import OrderType

from poly_boost.api.dependencies import get_order_service
from poly_boost.api.schemas.order_schemas import (
    MarketSellRequest,
    LimitSellRequest,
    MarketBuyRequest,
    LimitBuyRequest,
    ClaimRewardsRequest,
    OrderResponse,
    RewardsResponse,
    CancelOrderRequest,
    CancelOrderResponse,
    RedeemAllResponse,
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/{wallet_address}/sell/market", response_model=OrderResponse)
async def sell_position_market(
    wallet_address: str,
    request: MarketSellRequest
) -> OrderResponse:
    """
    Sell position at market price.
    
    - **wallet_address**: Wallet address to use for the operation
    - **token_id**: Token ID to sell
    - **amount**: Amount to sell (omit or null to sell all available balance)
    - **order_type**: FOK (Fill or Kill) or GTC (Good Till Cancel)
    """
    order_service = get_order_service(wallet_address)
    try:
        # Convert order type string to enum
        order_type_enum = OrderType.FOK if request.order_type == "FOK" else OrderType.GTC

        result = order_service.sell_position_market(
            token_id=request.token_id,
            amount=request.amount,
            order_type=order_type_enum
        )
        return OrderResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{wallet_address}/sell/limit", response_model=OrderResponse)
async def sell_position_limit(
    wallet_address: str,
    request: LimitSellRequest
) -> OrderResponse:
    """
    Sell position with limit price.
    
    - **wallet_address**: Wallet address to use for the operation
    - **token_id**: Token ID to sell
    - **price**: Limit price (must be between 0 and 1)
    - **amount**: Amount to sell (omit or null to sell all available balance)
    - **order_type**: GTC (Good Till Cancel) or GTD (Good Till Date)
    """
    order_service = get_order_service(wallet_address)
    try:
        # Convert order type string to enum
        order_type_enum = OrderType.GTC if request.order_type == "GTC" else OrderType.GTD

        result = order_service.sell_position_limit(
            token_id=request.token_id,
            price=request.price,
            amount=request.amount,
            order_type=order_type_enum
        )
        return OrderResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{wallet_address}/buy/market", response_model=OrderResponse)
async def buy_position_market(
    wallet_address: str,
    request: MarketBuyRequest
) -> OrderResponse:
    """
    Buy position at market price.
    
    - **wallet_address**: Wallet address to use for the operation
    - **token_id**: Token ID to buy
    - **amount**: Amount to buy
    - **order_type**: FOK (Fill or Kill) or GTC (Good Till Cancel)
    """
    order_service = get_order_service(wallet_address)
    try:
        # Convert order type string to enum
        order_type_enum = OrderType.FOK if request.order_type == "FOK" else OrderType.GTC

        result = order_service.buy_position_market(
            token_id=request.token_id,
            amount=request.amount,
            order_type=order_type_enum
        )
        return OrderResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{wallet_address}/buy/limit", response_model=OrderResponse)
async def buy_position_limit(
    wallet_address: str,
    request: LimitBuyRequest
) -> OrderResponse:
    """
    Buy position with limit price.
    
    - **wallet_address**: Wallet address to use for the operation
    - **token_id**: Token ID to buy
    - **price**: Limit price (must be between 0 and 1)
    - **amount**: Amount to buy
    - **order_type**: GTC (Good Till Cancel) or GTD (Good Till Date)
    """
    order_service = get_order_service(wallet_address)
    try:
        # Convert order type string to enum
        order_type_enum = OrderType.GTC if request.order_type == "GTC" else OrderType.GTD

        result = order_service.buy_position_limit(
            token_id=request.token_id,
            price=request.price,
            amount=request.amount,
            order_type=order_type_enum
        )
        return OrderResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{wallet_address}/rewards/claim", response_model=RewardsResponse)
async def claim_rewards(
    wallet_address: str,
    request: ClaimRewardsRequest
) -> RewardsResponse:
    """
    Claim rewards by redeeming positions from resolved markets.
    
    - **wallet_address**: Wallet address to use for the operation
    - **condition_id**: Condition ID of the resolved market
    - **token_id**: Token ID to redeem
    - **amount**: Requested amount to redeem (will be clamped to on-chain balance)
    """
    order_service = get_order_service(wallet_address)
    try:
        result = order_service.claim_rewards(
            condition_id=request.condition_id,
            token_id=request.token_id,
            amount=request.amount
        )
        return RewardsResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{wallet_address}", response_model=List[Dict[str, Any]])
async def get_orders(
    wallet_address: str,
    order_id: Optional[str] = None,
    condition_id: Optional[str] = None,
    token_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get active orders.
    
    - **wallet_address**: Wallet address to query orders for
    
    Query parameters:
    - **order_id**: Filter by order ID
    - **condition_id**: Filter by condition ID  
    - **token_id**: Filter by token ID
    """
    order_service = get_order_service(wallet_address)
    try:
        orders = order_service.get_orders(
            order_id=order_id,
            condition_id=condition_id,
            token_id=token_id
        )
        return orders
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{wallet_address}/cancel", response_model=CancelOrderResponse)
async def cancel_order(
    wallet_address: str,
    request: CancelOrderRequest
) -> CancelOrderResponse:
    """
    Cancel a specific order.
    
    - **wallet_address**: Wallet address to use for the operation
    - **order_id**: Order ID to cancel
    """
    order_service = get_order_service(wallet_address)
    try:
        result = order_service.cancel_order(request.order_id)
        return CancelOrderResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{wallet_address}/cancel/all", response_model=CancelOrderResponse)
async def cancel_all_orders(
    wallet_address: str
) -> CancelOrderResponse:
    """
    Cancel all active orders.

    - **wallet_address**: Wallet address to use for the operation
    """
    order_service = get_order_service(wallet_address)
    try:
        result = order_service.cancel_all_orders()
        return CancelOrderResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{wallet_address}/history", response_model=List[Dict[str, Any]])
async def get_trade_history(
    wallet_address: str,
    condition_id: Optional[str] = None,
    token_id: Optional[str] = None,
    trade_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get trade history for a wallet.

    - **wallet_address**: Wallet address to query trade history for

    Query parameters:
    - **condition_id**: Filter by condition ID
    - **token_id**: Filter by token ID
    - **trade_id**: Filter by specific trade ID
    """
    order_service = get_order_service(wallet_address)
    try:
        trades = order_service.get_trade_history(
            condition_id=condition_id,
            token_id=token_id,
            trade_id=trade_id
        )
        return trades
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{wallet_address}/rewards/claim-all", response_model=RedeemAllResponse)
async def claim_all_rewards(
    wallet_address: str
) -> RedeemAllResponse:
    """
    Claim rewards for all redeemable positions.

    This endpoint will automatically redeem all positions that are marked as redeemable
    for the specified wallet. Individual redemption failures will not stop the process.

    - **wallet_address**: Wallet address to use for the operation

    Returns:
    - **status**: Overall operation status (success/partial/failed)
    - **total_positions**: Total number of redeemable positions found
    - **successful**: Number of successful redemptions
    - **failed**: Number of failed redemptions
    - **results**: List of successful redemption details
    - **errors**: List of error details for failed redemptions
    """
    order_service = get_order_service(wallet_address)
    try:
        result = order_service.redeem_all_positions()
        return RedeemAllResponse(**result)
    except ValueError as e:
        # Configuration error (e.g., PositionService not configured)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Unexpected errors
        raise HTTPException(status_code=500, detail=str(e))
