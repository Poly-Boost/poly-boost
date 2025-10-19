"""
Pydantic schemas for order-related API requests and responses.
"""

from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator


class MarketSellRequest(BaseModel):
    """Request schema for market sell order."""
    
    token_id: str = Field(..., description="Token ID to sell")
    amount: Optional[float] = Field(None, description="Amount to sell (None = sell all)")
    order_type: str = Field("FOK", description="Order type (FOK or GTC)")
    
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v
    
    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v):
        if v not in ["FOK", "GTC"]:
            raise ValueError("Order type must be FOK or GTC")
        return v


class LimitSellRequest(BaseModel):
    """Request schema for limit sell order."""
    
    token_id: str = Field(..., description="Token ID to sell")
    price: float = Field(..., description="Limit price (0 < price < 1)")
    amount: Optional[float] = Field(None, description="Amount to sell (None = sell all)")
    order_type: str = Field("GTC", description="Order type (GTC or GTD)")
    
    @field_validator("price")
    @classmethod
    def validate_price(cls, v):
        if not (0 < v < 1):
            raise ValueError("Price must be between 0 and 1")
        return v
    
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v
    
    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v):
        if v not in ["GTC", "GTD"]:
            raise ValueError("Order type must be GTC or GTD")
        return v


class MarketBuyRequest(BaseModel):
    """Request schema for market buy order."""
    
    token_id: str = Field(..., description="Token ID to buy")
    amount: float = Field(..., description="Amount to buy", gt=0)
    order_type: str = Field("FOK", description="Order type (FOK or GTC)")
    
    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v):
        if v not in ["FOK", "GTC"]:
            raise ValueError("Order type must be FOK or GTC")
        return v


class LimitBuyRequest(BaseModel):
    """Request schema for limit buy order."""
    
    token_id: str = Field(..., description="Token ID to buy")
    price: float = Field(..., description="Limit price (0 < price < 1)")
    amount: float = Field(..., description="Amount to buy", gt=0)
    order_type: str = Field("GTC", description="Order type (GTC or GTD)")
    
    @field_validator("price")
    @classmethod
    def validate_price(cls, v):
        if not (0 < v < 1):
            raise ValueError("Price must be between 0 and 1")
        return v
    
    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v):
        if v not in ["GTC", "GTD"]:
            raise ValueError("Order type must be GTC or GTD")
        return v


class ClaimRewardsRequest(BaseModel):
    """Request schema for claiming rewards."""
    
    condition_id: str = Field(..., description="Condition ID of the resolved market")
    amounts: List[float] = Field(..., description="Amounts to redeem [outcome1, outcome2]")
    token_ids: Optional[List[Optional[str]]] = Field(
        None, 
        description="Token IDs for balance query [token1_id, token2_id]. If provided, actual balances will be queried."
    )
    
    @field_validator("amounts")
    @classmethod
    def validate_amounts(cls, v):
        if len(v) != 2:
            raise ValueError("Amounts must contain exactly 2 values")
        if any(amount < 0 for amount in v):
            raise ValueError("Amounts must be non-negative")
        return v
    
    @field_validator("token_ids")
    @classmethod
    def validate_token_ids(cls, v):
        if v is not None and len(v) != 2:
            raise ValueError("Token IDs must contain exactly 2 values (can be null)")
        return v


class OrderResponse(BaseModel):
    """Response schema for order operations."""
    
    status: str = Field(..., description="Operation status")
    order_id: Optional[str] = Field(None, description="Order ID (if applicable)")
    token_id: Optional[str] = Field(None, description="Token ID")
    amount: Optional[float] = Field(None, description="Order amount")
    price: Optional[float] = Field(None, description="Order price")
    side: Optional[str] = Field(None, description="Order side (BUY/SELL)")
    order_type: Optional[str] = Field(None, description="Order type")
    message: Optional[str] = Field(None, description="Additional message")
    response: Optional[Any] = Field(None, description="Raw API response")


class RewardsResponse(BaseModel):
    """Response schema for reward claiming."""
    
    status: str = Field(..., description="Operation status")
    condition_id: str = Field(..., description="Condition ID")
    amounts: List[float] = Field(..., description="Redeemed amounts")
    message: str = Field(..., description="Operation message")


class CancelOrderRequest(BaseModel):
    """Request schema for cancelling an order."""
    
    order_id: str = Field(..., description="Order ID to cancel")


class CancelOrderResponse(BaseModel):
    """Response schema for order cancellation."""
    
    status: str = Field(..., description="Operation status")
    order_id: Optional[str] = Field(None, description="Cancelled order ID")
    response: Optional[Any] = Field(None, description="Raw API response")
