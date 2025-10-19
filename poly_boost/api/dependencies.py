"""
FastAPI dependency injection.

Provides shared dependencies for API routes.
"""

from typing import Optional, Dict
from functools import lru_cache
import os
import logging

from py_clob_client.client import ClobClient
from polymarket_apis.clients.data_client import PolymarketDataClient
from polymarket_apis.clients.clob_client import PolymarketClobClient
from polymarket_apis.clients.web3_client import PolymarketWeb3Client
import httpx

from poly_boost.core.config_loader import load_config
from poly_boost.core.in_memory_activity_queue import InMemoryActivityQueue
from poly_boost.services.position_service import PositionService
from poly_boost.services.trading_service import TradingService
from poly_boost.services.wallet_service import WalletService
from poly_boost.services.order_service import OrderService

logger = logging.getLogger(__name__)


# Global instances (initialized on startup)
_activity_queue: Optional[InMemoryActivityQueue] = None
_position_service: Optional[PositionService] = None
_trading_service: Optional[TradingService] = None
_wallet_service: Optional[WalletService] = None
_order_service: Optional[OrderService] = None
_config: Optional[dict] = None
_clob_client: Optional[PolymarketClobClient] = None
_web3_client: Optional[PolymarketWeb3Client] = None

# Cache for order services per wallet
_order_service_cache: Dict[str, OrderService] = {}


def initialize_services():
    """
    Initialize all services on application startup.

    This should be called once when the FastAPI app starts.
    """
    global _activity_queue, _position_service, _trading_service, _wallet_service, _order_service, _config
    global _clob_client, _web3_client

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

    # Get API configuration
    api_config = _config.get('polymarket_api', {})
    proxy = api_config.get('proxy')
    timeout = api_config.get('timeout', 30.0)
    verify_ssl = api_config.get('verify_ssl', True)

    # Prepare httpx client kwargs (similar to wallet_monitor.py)
    client_kwargs = {
        "http2": True,
        "timeout": timeout,
        "verify": verify_ssl
    }
    if proxy:
        client_kwargs["proxy"] = proxy
    
    # Suppress SSL warnings if verification is disabled
    if not verify_ssl:
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except ImportError:
            pass

    # Get user wallet configuration (first wallet)
    user_wallets = _config.get('user_wallets', [])
    if not user_wallets:
        raise ValueError(
            "No user wallets configured. Please add user_wallets to config.yaml for order operations"
        )

    wallet_config = user_wallets[0]
    private_key_env = wallet_config.get('private_key_env')
    private_key = os.getenv(private_key_env) if private_key_env else None
    proxy_address = wallet_config.get('proxy_address')
    signature_type = wallet_config.get('signature_type', 2)
    
    if not (private_key and proxy_address):
        raise ValueError(
            "Order service requires wallet configuration with private_key and proxy_address. "
            "Please configure user_wallets in config.yaml"
        )
    
    # Create a temporary client with proxy to get API credentials first
    logger.info("Creating temporary HTTP client to obtain Polymarket API credentials...")
    temp_client = httpx.Client(**client_kwargs)
    
    from polymarket_apis.utilities.signing.signer import Signer
    from polymarket_apis.utilities.headers import create_level_1_headers
    from polymarket_apis.types.clob_types import ApiCreds
    
    # Get or create API credentials with proper proxy configuration
    signer = Signer(private_key=private_key, chain_id=137)
    headers = create_level_1_headers(signer, None)
    
    try:
        # Try to create new API key
        logger.info("Attempting to create new Polymarket API key...")
        response = temp_client.post(
            "https://clob.polymarket.com/auth/api-key",
            headers=headers
        )
        response.raise_for_status()
        creds = ApiCreds(**response.json())
        logger.info("Successfully created new API credentials")
    except Exception as e:
        # If creation fails, try to derive existing key
        logger.info(f"API key creation failed ({e}), attempting to derive existing key...")
        try:
            response = temp_client.get(
                "https://clob.polymarket.com/auth/derive-api-key",
                headers=headers
            )
            response.raise_for_status()
            creds = ApiCreds(**response.json())
            logger.info("Successfully derived existing API credentials")
        except Exception as derive_error:
            logger.error(f"Failed to obtain API credentials: {derive_error}")
            temp_client.close()
            raise RuntimeError(
                "Failed to obtain Polymarket API credentials. "
                "Please check your network connection and proxy settings."
            ) from derive_error
    
    temp_client.close()
    logger.info("Temporary client closed")
    
    # Now initialize CLOB client with credentials (won't make API call in __init__)
    logger.info("Initializing PolymarketClobClient with obtained credentials...")
    _clob_client = PolymarketClobClient(
        private_key=private_key,
        proxy_address=proxy_address,
        signature_type=signature_type,
        chain_id=137,  # Polygon mainnet
        creds=creds  # Pass credentials to skip API call during init
    )
    # Replace default clients with configured ones
    _clob_client.client = httpx.Client(**client_kwargs)
    _clob_client.async_client = httpx.AsyncClient(**client_kwargs)
    logger.info("PolymarketClobClient initialized successfully")
    
    # Initialize Web3 client
    _web3_client = PolymarketWeb3Client(
        private_key=private_key,
        chain_id=137
    )

    # Create old CLOB client for backward compatibility (read-only operations)
    legacy_clob_client = ClobClient(
        host="https://clob.polymarket.com",
        key="",  # Read-only operations may not need key
        chain_id=137  # Polygon mainnet
    )

    # Create Data API client with configured httpx client
    data_client = PolymarketDataClient()
    data_client.client = httpx.Client(**client_kwargs)

    # Initialize services
    _position_service = PositionService(legacy_clob_client, data_client)
    _trading_service = TradingService(_activity_queue)
    _wallet_service = WalletService(legacy_clob_client)
    
    # Determine the wallet address to use based on signature_type
    from web3 import Web3
    operation_address_raw = (
        wallet_config.get('address') if signature_type == 0 
        else wallet_config.get('proxy_address')
    )
    # Convert to checksum address (required by web3.py)
    operation_address = Web3.to_checksum_address(operation_address_raw)
    
    _order_service = OrderService(
        _clob_client, 
        _web3_client, 
        signature_type,
        wallet_address=operation_address
    )


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


def get_order_service() -> OrderService:
    """Get order service instance."""
    if _order_service is None:
        raise RuntimeError("Services not initialized. Call initialize_services() first.")
    return _order_service


def get_order_service_for_wallet(wallet_address: str) -> OrderService:
    """
    Get or create an OrderService for a specific wallet address.
    
    Args:
        wallet_address: Wallet address (can be EOA address or proxy address)
        
    Returns:
        OrderService instance configured for the wallet
        
    Raises:
        ValueError: If wallet not found in configuration
    """
    if _config is None:
        raise RuntimeError("Services not initialized. Call initialize_services() first.")
    
    # Check cache first
    wallet_address_lower = wallet_address.lower()
    if wallet_address_lower in _order_service_cache:
        return _order_service_cache[wallet_address_lower]
    
    # Find wallet configuration
    user_wallets = _config.get('user_wallets', [])
    wallet_config = None
    
    for wallet in user_wallets:
        # Match by address or proxy_address
        if (wallet.get('address', '').lower() == wallet_address_lower or 
            wallet.get('proxy_address', '').lower() == wallet_address_lower):
            wallet_config = wallet
            break
    
    if not wallet_config:
        raise ValueError(
            f"Wallet address '{wallet_address}' not found in configuration. "
            f"Please add it to user_wallets in config.yaml"
        )
    
    # Get wallet configuration
    private_key_env = wallet_config.get('private_key_env')
    private_key = os.getenv(private_key_env) if private_key_env else None
    proxy_address = wallet_config.get('proxy_address')
    signature_type = wallet_config.get('signature_type', 2)
    wallet_name = wallet_config.get('name', 'Unknown')
    
    if not private_key:
        raise ValueError(
            f"Private key not found for wallet '{wallet_name}'. "
            f"Please set environment variable '{private_key_env}'"
        )
    
    # For signature_type 1 or 2, proxy_address is required
    if signature_type in [1, 2] and not proxy_address:
        raise ValueError(
            f"Wallet '{wallet_name}' with signature_type={signature_type} requires proxy_address"
        )
    
    logger.info(
        f"Creating OrderService for wallet '{wallet_name}' "
        f"(address={wallet_config.get('address')}, signature_type={signature_type})"
    )
    
    # Get API configuration
    api_config = _config.get('polymarket_api', {})
    proxy = api_config.get('proxy')
    timeout = api_config.get('timeout', 30.0)
    verify_ssl = api_config.get('verify_ssl', True)
    
    # Prepare httpx client kwargs
    client_kwargs = {
        "http2": True,
        "timeout": timeout,
        "verify": verify_ssl
    }
    if proxy:
        client_kwargs["proxy"] = proxy
    
    # Create temporary client to get API credentials
    temp_client = httpx.Client(**client_kwargs)
    
    from polymarket_apis.utilities.signing.signer import Signer
    from polymarket_apis.utilities.headers import create_level_1_headers
    from polymarket_apis.types.clob_types import ApiCreds
    
    signer = Signer(private_key=private_key, chain_id=137)
    headers = create_level_1_headers(signer, None)
    
    try:
        # Try to derive existing API key first (more common scenario)
        logger.info(f"Obtaining API credentials for wallet '{wallet_name}'...")
        response = temp_client.get(
            "https://clob.polymarket.com/auth/derive-api-key",
            headers=headers
        )
        response.raise_for_status()
        creds = ApiCreds(**response.json())
    except Exception as e:
        # If derive fails, try to create new API key
        logger.info(f"Derive failed, creating new API key for wallet '{wallet_name}'...")
        try:
            response = temp_client.post(
                "https://clob.polymarket.com/auth/api-key",
                headers=headers
            )
            response.raise_for_status()
            creds = ApiCreds(**response.json())
        except Exception as create_error:
            temp_client.close()
            raise RuntimeError(
                f"Failed to obtain API credentials for wallet '{wallet_name}': {create_error}"
            ) from create_error
    
    temp_client.close()
    
    # Initialize CLOB client
    clob_client = PolymarketClobClient(
        private_key=private_key,
        proxy_address=proxy_address if signature_type in [1, 2] else wallet_config.get('address'),
        signature_type=signature_type,
        chain_id=137,
        creds=creds
    )
    clob_client.client = httpx.Client(**client_kwargs)
    clob_client.async_client = httpx.AsyncClient(**client_kwargs)
    
    # Initialize Web3 client
    web3_client = PolymarketWeb3Client(
        private_key=private_key,
        chain_id=137
    )
    
    # Determine the wallet address to use for operations based on signature_type
    # For EOA (signature_type=0): use the original wallet address
    # For Proxy (signature_type=1/2): use the proxy_address
    from web3 import Web3
    
    operation_address_raw = (
        wallet_config.get('address') if signature_type == 0 
        else wallet_config.get('proxy_address')
    )
    
    # Convert to checksum address (required by web3.py)
    operation_address = Web3.to_checksum_address(operation_address_raw)
    
    logger.info(
        f"Using operation address: {operation_address} "
        f"(signature_type={signature_type}, {'EOA' if signature_type == 0 else 'Proxy'})"
    )
    
    # Create OrderService with the correct operation address
    order_service = OrderService(
        clob_client, 
        web3_client, 
        signature_type,
        wallet_address=operation_address
    )
    
    # Cache the service
    _order_service_cache[wallet_address_lower] = order_service
    
    logger.info(f"OrderService created and cached for wallet '{wallet_name}'")
    
    return order_service
