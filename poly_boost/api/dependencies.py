"""
FastAPI dependency injection.

Provides shared dependencies for API routes.
"""

from typing import Optional
from functools import lru_cache

from py_clob_client.client import ClobClient

from poly_boost.core.config_loader import load_config
from poly_boost.core.in_memory_activity_queue import InMemoryActivityQueue
from poly_boost.services.position_service import PositionService
from poly_boost.services.trading_service import TradingService
from poly_boost.services.wallet_service import WalletService


# Global instances (initialized on startup)
_activity_queue: Optional[InMemoryActivityQueue] = None
_position_service: Optional[PositionService] = None
_trading_service: Optional[TradingService] = None
_wallet_service: Optional[WalletService] = None
_config: Optional[dict] = None


def initialize_services():
    """
    Initialize all services on application startup.

    This should be called once when the FastAPI app starts.
    """
    global _activity_queue, _position_service, _trading_service, _wallet_service, _config

    # Load configuration
    _config = load_config()

    # Create activity queue
    queue_config = _config.get('queue', {})
    queue_type = queue_config.get('type', 'memory')

    if queue_type == 'memory':
        memory_config = queue_config.get('memory', {})
        max_workers = memory_config.get('max_workers', 10)
        _activity_queue = InMemoryActivityQueue(max_workers=max_workers)
    else:
        raise NotImplementedError(f"Queue type '{queue_type}' not supported")

    # Create CLOB client (for position/wallet services)
    api_config = _config.get('polymarket_api', {})
    proxy = api_config.get('proxy')
    verify_ssl = api_config.get('verify_ssl', True)

    # TODO: Initialize ClobClient properly with keys
    # For now, create a basic instance
    clob_client = ClobClient(
        host="https://clob.polymarket.com",
        key="",  # Read-only operations may not need key
        chain_id=137  # Polygon mainnet
    )

    # Initialize services
    _position_service = PositionService(clob_client)
    _trading_service = TradingService(_activity_queue)
    _wallet_service = WalletService(clob_client)


def get_config() -> dict:
    """Get application configuration."""
    if _config is None:
        raise RuntimeError("Services not initialized. Call initialize_services() first.")
    return _config


def get_activity_queue() -> InMemoryActivityQueue:
    """Get activity queue instance."""
    if _activity_queue is None:
        raise RuntimeError("Services not initialized. Call initialize_services() first.")
    return _activity_queue


def get_position_service() -> PositionService:
    """Get position service instance."""
    if _position_service is None:
        raise RuntimeError("Services not initialized. Call initialize_services() first.")
    return _position_service


def get_trading_service() -> TradingService:
    """Get trading service instance."""
    if _trading_service is None:
        raise RuntimeError("Services not initialized. Call initialize_services() first.")
    return _trading_service


def get_wallet_service() -> WalletService:
    """Get wallet service instance."""
    if _wallet_service is None:
        raise RuntimeError("Services not initialized. Call initialize_services() first.")
    return _wallet_service
