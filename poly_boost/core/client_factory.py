"""
ClientFactory - Creates and caches API clients for wallets.

Handles client creation, credential management, and connection pooling.
"""

from typing import Dict, Optional
import httpx
import logging

from polymarket_apis.clients.clob_client import PolymarketClobClient
from polymarket_apis.clients.web3_client import PolymarketWeb3Client
from polymarket_apis.utilities.signing.signer import Signer
from polymarket_apis.utilities.headers import create_level_1_headers
from polymarket_apis.types.clob_types import ApiCreds

from poly_boost.core.wallet import Wallet, ProxyWallet

logger = logging.getLogger(__name__)


class ClientFactory:
    """
    Factory for creating and caching Polymarket API clients.

    Responsibilities:
    1. Create CLOB and Web3 clients for wallets
    2. Manage API credentials
    3. Handle HTTP client pooling
    4. Cache clients per wallet
    """

    def __init__(self, api_config: dict):
        """
        Initialize client factory.

        Args:
            api_config: API configuration dictionary containing:
                - proxy: HTTP proxy URL (optional)
                - timeout: Request timeout in seconds
                - verify_ssl: Whether to verify SSL certificates
        """
        self.api_config = api_config

        # Client caches (indexed by api_address)
        self._clob_cache: Dict[str, PolymarketClobClient] = {}
        self._web3_cache: Dict[str, PolymarketWeb3Client] = {}

        # Shared HTTP client for connection pooling
        self._shared_http_client: Optional[httpx.Client] = None
        self._shared_async_client: Optional[httpx.AsyncClient] = None

    def _get_http_client(self) -> httpx.Client:
        """
        Get shared HTTP client (singleton).

        Returns:
            Configured httpx.Client instance
        """
        if self._shared_http_client is None:
            client_kwargs = {
                "http2": True,
                "timeout": self.api_config.get('timeout', 30.0),
                "verify": self.api_config.get('verify_ssl', True)
            }

            if proxy := self.api_config.get('proxy'):
                client_kwargs["proxy"] = proxy

            self._shared_http_client = httpx.Client(**client_kwargs)
            logger.info("Shared HTTP client created")

            # Suppress SSL warnings if verification disabled
            if not self.api_config.get('verify_ssl', True):
                try:
                    import urllib3
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                except ImportError:
                    pass

        return self._shared_http_client

    def _get_async_http_client(self) -> httpx.AsyncClient:
        """
        Get shared async HTTP client (singleton).

        Returns:
            Configured httpx.AsyncClient instance
        """
        if self._shared_async_client is None:
            client_kwargs = {
                "http2": True,
                "timeout": self.api_config.get('timeout', 30.0),
                "verify": self.api_config.get('verify_ssl', True)
            }

            if proxy := self.api_config.get('proxy'):
                client_kwargs["proxy"] = proxy

            self._shared_async_client = httpx.AsyncClient(**client_kwargs)
            logger.info("Shared async HTTP client created")

        return self._shared_async_client

    def get_clob_client(self, wallet: Wallet) -> PolymarketClobClient:
        """
        Get or create CLOB client for wallet.

        Args:
            wallet: Wallet instance

        Returns:
            Configured PolymarketClobClient

        Raises:
            ValueError: If wallet is read-only or private key not available
        """
        cache_key = wallet.api_address.lower()

        # Return cached client if available
        if cache_key in self._clob_cache:
            logger.debug(f"Using cached CLOB client for wallet '{wallet.name}'")
            return self._clob_cache[cache_key]

        # Validate wallet can create client
        if not wallet.requires_private_key:
            raise ValueError(
                f"Wallet '{wallet.name}' is read-only, cannot create CLOB client"
            )

        private_key = wallet.get_private_key()
        if not private_key:
            raise ValueError(
                f"Private key not available for wallet '{wallet.name}'. "
                f"Please set the required environment variable."
            )

        logger.info(f"Creating CLOB client for wallet '{wallet.name}'...")

        # Get API credentials
        creds = self._get_api_credentials(wallet, private_key)

        # Determine proxy_address parameter based on wallet type
        if isinstance(wallet, ProxyWallet):
            proxy_address = wallet.proxy_address
        else:
            # For EOA wallets, pass the EOA address
            proxy_address = wallet.eoa_address

        # Create CLOB client
        clob_client = PolymarketClobClient(
            private_key=private_key,
            proxy_address=proxy_address,
            signature_type=wallet.signature_type,
            chain_id=137,  # Polygon mainnet
            creds=creds
        )

        # Replace default HTTP clients with shared instances
        clob_client.client = self._get_http_client()
        clob_client.async_client = self._get_async_http_client()

        # Cache and return
        self._clob_cache[cache_key] = clob_client
        logger.info(f"CLOB client created for wallet '{wallet.name}'")

        return clob_client

    def get_web3_client(self, wallet: Wallet) -> PolymarketWeb3Client:
        """
        Get or create Web3 client for wallet.

        Args:
            wallet: Wallet instance

        Returns:
            Configured PolymarketWeb3Client

        Raises:
            ValueError: If wallet is read-only or private key not available
        """
        cache_key = wallet.api_address.lower()

        # Return cached client if available
        if cache_key in self._web3_cache:
            logger.debug(f"Using cached Web3 client for wallet '{wallet.name}'")
            return self._web3_cache[cache_key]

        # Validate wallet can create client
        if not wallet.requires_private_key:
            raise ValueError(
                f"Wallet '{wallet.name}' is read-only, cannot create Web3 client"
            )

        private_key = wallet.get_private_key()
        if not private_key:
            raise ValueError(
                f"Private key not available for wallet '{wallet.name}'. "
                f"Please set the required environment variable."
            )

        logger.info(f"Creating Web3 client for wallet '{wallet.name}'...")

        # Create Web3 client
        web3_client = PolymarketWeb3Client(
            private_key=private_key,
            chain_id=137  # Polygon mainnet
        )

        # Cache and return
        self._web3_cache[cache_key] = web3_client
        logger.info(f"Web3 client created for wallet '{wallet.name}'")

        return web3_client

    def _get_api_credentials(self, wallet: Wallet, private_key: str) -> ApiCreds:
        """
        Get Polymarket API credentials for wallet.

        Tries to derive existing credentials first, creates new ones if needed.

        Args:
            wallet: Wallet instance
            private_key: Wallet private key

        Returns:
            API credentials

        Raises:
            RuntimeError: If credential retrieval fails
        """
        http_client = self._get_http_client()
        signer = Signer(private_key=private_key, chain_id=137)
        headers = create_level_1_headers(signer, None)

        try:
            # Try to derive existing API key first (most common case)
            logger.debug(f"Deriving API credentials for wallet '{wallet.name}'...")
            response = http_client.get(
                "https://clob.polymarket.com/auth/derive-api-key",
                headers=headers
            )
            response.raise_for_status()
            creds = ApiCreds(**response.json())
            logger.info(f"API credentials derived for wallet '{wallet.name}'")
            return creds

        except Exception as derive_error:
            # If derive fails, try to create new API key
            logger.debug(
                f"Derive failed for wallet '{wallet.name}', creating new API key..."
            )
            try:
                response = http_client.post(
                    "https://clob.polymarket.com/auth/api-key",
                    headers=headers
                )
                response.raise_for_status()
                creds = ApiCreds(**response.json())
                logger.info(f"New API credentials created for wallet '{wallet.name}'")
                return creds

            except Exception as create_error:
                logger.error(
                    f"Failed to obtain API credentials for wallet '{wallet.name}': "
                    f"derive_error={derive_error}, create_error={create_error}"
                )
                raise RuntimeError(
                    f"Failed to obtain Polymarket API credentials for wallet '{wallet.name}'. "
                    f"Please check your network connection and proxy settings."
                ) from create_error

    def clear_cache(self, wallet_address: Optional[str] = None):
        """
        Clear cached clients.

        Args:
            wallet_address: Specific wallet address to clear, or None to clear all
        """
        if wallet_address:
            addr_lower = wallet_address.lower()
            self._clob_cache.pop(addr_lower, None)
            self._web3_cache.pop(addr_lower, None)
            logger.info(f"Cleared cached clients for wallet {wallet_address}")
        else:
            self._clob_cache.clear()
            self._web3_cache.clear()
            logger.info("Cleared all cached clients")

    def close(self):
        """Close all HTTP clients and clear caches."""
        if self._shared_http_client:
            self._shared_http_client.close()
            self._shared_http_client = None

        if self._shared_async_client:
            # Async client needs to be awaited, but we can't do that here
            # In practice, FastAPI will handle cleanup
            self._shared_async_client = None

        self.clear_cache()
        logger.info("ClientFactory closed")
