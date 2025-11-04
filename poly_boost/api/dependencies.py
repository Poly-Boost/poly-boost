"""
FastAPI dependency injection.

Provides shared dependencies for API routes.
"""

from typing import Optional, Dict
import logging

from poly_boost.core.config_loader import load_config
from poly_boost.core.in_memory_activity_queue import InMemoryActivityQueue
from poly_boost.core.wallet_manager import WalletManager
from poly_boost.core.client_factory import ClientFactory
from poly_boost.services.position_service import PositionService
from poly_boost.services.trading_service import TradingService
from poly_boost.services.wallet_service import WalletService
from poly_boost.services.order_service import OrderService
from poly_boost.services.activity_service import ActivityService

logger = logging.getLogger(__name__)


# Global instances (initialized on startup)
_config: Optional[dict] = None
_activity_queue: Optional[InMemoryActivityQueue] = None
_wallet_manager: Optional[WalletManager] = None
_client_factory: Optional[ClientFactory] = None
_position_service: Optional[PositionService] = None
_trading_service: Optional[TradingService] = None
_wallet_service: Optional[WalletService] = None
_activity_service: Optional[ActivityService] = None

# Cache for order services per wallet (indexed by api_address)
_order_service_cache: Dict[str, OrderService] = {}


def initialize_services():
    """
    Initialize all services on application startup.

    This should be called once when the FastAPI app starts.
    """
    global _config, _activity_queue, _wallet_manager, _client_factory
    global _position_service, _trading_service, _wallet_service, _activity_service

    # Load configuration
    _config = load_config()
    logger.info("Configuration loaded")

    # Initialize WalletManager
    logger.info("Initializing WalletManager...")
    _wallet_manager = WalletManager.from_config(_config)
    logger.info(
        f"WalletManager initialized with {len(_wallet_manager.list_all())} wallets "
        f"({len(_wallet_manager.list_tradable())} tradable, "
        f"{len(_wallet_manager.list_readonly())} read-only)"
    )

    # Initialize ClientFactory
    api_config = _config.get('polymarket_api', {})
    _client_factory = ClientFactory(api_config)
    logger.info("ClientFactory initialized")

    # Create activity queue
    queue_config = _config.get('queue', {})
    queue_type = queue_config.get('type', 'memory')

    if queue_type == 'memory':
        memory_config = queue_config.get('memory', {})
        max_workers = memory_config.get('max_workers', 10)
        _activity_queue = InMemoryActivityQueue(max_workers=max_workers)
        logger.info(f"Activity queue initialized with {max_workers} workers")
    else:
        raise NotImplementedError(f"Queue type '{queue_type}' not supported")

    # Create shared clients via factory
    legacy_clob_client = _client_factory.get_legacy_clob_client()
    data_client = _client_factory.get_data_client()

    # Get Polygon RPC URL for on-chain queries
    polygon_rpc_config = _config.get('polygon_rpc', {})
    polygon_rpc_url = polygon_rpc_config.get('url', 'https://polygon-rpc.com')

    # Initialize services with WalletManager injection
    _position_service = PositionService(
        legacy_clob_client,
        data_client,
        wallet_manager=_wallet_manager  # Inject WalletManager for wallet resolution
    )
    _trading_service = TradingService(_activity_queue)
    _wallet_service = WalletService(
        legacy_clob_client,
        wallet_manager=_wallet_manager,
        client_factory=_client_factory,  # Inject ClientFactory for wallet-specific clients
        polygon_rpc_url=polygon_rpc_url  # For on-chain balance queries
    )
    _activity_service = ActivityService(
        data_client,
        wallet_manager=_wallet_manager  # Inject WalletManager for wallet resolution
    )

    logger.info("All services initialized successfully")


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


def get_wallet_manager() -> WalletManager:
    """Get wallet manager instance."""
    if _wallet_manager is None:
        raise RuntimeError("Services not initialized. Call initialize_services() first.")
    return _wallet_manager


def get_client_factory() -> ClientFactory:
    """Get client factory instance."""
    if _client_factory is None:
        raise RuntimeError("Services not initialized. Call initialize_services() first.")
    return _client_factory


def get_activity_service() -> ActivityService:
    """Get activity service instance."""
    if _activity_service is None:
        raise RuntimeError("Services not initialized. Call initialize_services() first.")
    return _activity_service


def get_order_service(wallet_address: str) -> OrderService:
    """
    Get or create an OrderService for a specific wallet address.

    Args:
        wallet_address: Wallet address (can be api_address, eoa_address, or proxy_address)

    Returns:
        OrderService instance configured for the wallet

    Raises:
        ValueError: If wallet not found in configuration
        RuntimeError: If services not initialized
    """
    if _wallet_manager is None or _client_factory is None:
        raise RuntimeError("Services not initialized. Call initialize_services() first.")

    # Get wallet from manager (supports multiple address formats)
    wallet = _wallet_manager.get_or_raise(wallet_address)

    # Check cache (use api_address as key)
    cache_key = wallet.api_address.lower()
    if cache_key in _order_service_cache:
        logger.debug(f"Using cached OrderService for wallet '{wallet.name}'")
        return _order_service_cache[cache_key]

    logger.info(f"Creating OrderService for wallet '{wallet.name}'...")

    # Create clients using factory
    clob_client = _client_factory.get_clob_client(wallet)
    web3_client = _client_factory.get_web3_client(wallet)

    # Create OrderService with wallet abstraction
    order_service = OrderService(wallet, clob_client, web3_client)

    # Cache the service
    _order_service_cache[cache_key] = order_service
    logger.info(f"OrderService created and cached for wallet '{wallet.name}'")

    return order_service
