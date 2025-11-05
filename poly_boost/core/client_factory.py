"""
ClientFactory - Creates and caches API clients for wallets.

Handles client creation, credential management, and connection pooling.
"""

from typing import Dict, Literal, Optional, cast
import httpx
import logging
import requests

from py_clob_client.client import ClobClient as LegacyClobClient

from polymarket_apis.clients.clob_client import PolymarketClobClient
from polymarket_apis.clients.web3_client import PolymarketWeb3Client
from polymarket_apis.clients.data_client import PolymarketDataClient
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
        self._data_client: Optional[PolymarketDataClient] = None
        self._legacy_clob_client: Optional[LegacyClobClient] = None

        # Shared HTTP client for connection pooling
        self._shared_http_client: Optional[httpx.Client] = None
        self._shared_async_client: Optional[httpx.AsyncClient] = None

        # Tracking for requests patching (used by legacy client)
        self._requests_defaults_applied: bool = False
        self._original_requests_method = None

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

    # Public accessors for shared HTTP clients so other components can reuse
    def get_http_client(self) -> httpx.Client:
        """Public wrapper to get the shared httpx.Client with configured proxy/SSL."""
        return self._get_http_client()

    def get_async_http_client(self) -> httpx.AsyncClient:
        """Public wrapper to get the shared httpx.AsyncClient with configured proxy/SSL."""
        return self._get_async_http_client()

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

        # Resolve the on-chain address to use for signing/funding
        # Use the same address derivation logic as PolymarketWeb3Client
        sig_type = wallet.signature_type

        # Type guard to ensure sig_type is valid for SDK
        if sig_type not in (0, 1, 2):
            raise ValueError(
                f"Invalid signature_type {sig_type} for wallet '{wallet.name}'. "
                f"Expected 0 (EOA), 1 (Proxy), or 2 (Safe)."
            )

        # Cast to Literal type for SDK compatibility
        sdk_sig_type = cast(Literal[0, 1, 2], sig_type)

        match sig_type:
            case 0:
                # EOA wallet - use the EOA address directly
                address = wallet.eoa_address
            case 1:
                # Proxy wallet - use the proxy address
                if isinstance(wallet, ProxyWallet):
                    address = wallet.proxy_address
                else:
                    # Fallback: derive proxy address using Web3Client
                    temp_web3 = PolymarketWeb3Client(
                        private_key=private_key,
                        signature_type=1,
                        chain_id=137,
                    )
                    address = temp_web3.address
            case 2:
                # Safe wallet - derive address using Web3Client
                temp_web3 = PolymarketWeb3Client(
                    private_key=private_key,
                    signature_type=2,
                    chain_id=137,
                )
                address = temp_web3.address
            case _:
                raise ValueError(
                    f"Unknown signature_type {sig_type} for wallet '{wallet.name}'"
                )

        # Create CLOB client
        clob_client = PolymarketClobClient(
            private_key=private_key,
            address=address,
            creds=creds,
            chain_id=137,  # Polygon mainnet
            signature_type=sdk_sig_type,
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

        # Type guard to ensure signature_type is valid for SDK
        sig_type = wallet.signature_type
        if sig_type not in (0, 1, 2):
            raise ValueError(
                f"Invalid signature_type {sig_type} for wallet '{wallet.name}'. "
                f"Expected 0 (EOA), 1 (Proxy), or 2 (Safe)."
            )

        # Cast to Literal type for SDK compatibility
        sdk_sig_type = cast(Literal[0, 1, 2], sig_type)

        # Create Web3 client
        web3_client = PolymarketWeb3Client(
            private_key=private_key,
            signature_type=sdk_sig_type,
            chain_id=137,  # Polygon mainnet
        )

        # Ensure Web3 client uses shared HTTP clients if supported by the SDK
        if hasattr(web3_client, "client"):
            web3_client.client = self._get_http_client()
        if hasattr(web3_client, "async_client"):
            web3_client.async_client = self._get_async_http_client()

        # Cache and return
        self._web3_cache[cache_key] = web3_client
        logger.info(f"Web3 client created for wallet '{wallet.name}'")

        return web3_client

    def get_data_client(self) -> PolymarketDataClient:
        """
        Get or create shared Polymarket Data API client.

        Ensures the client uses the shared HTTP clients so that proxy and
        SSL verification settings are consistently applied.

        Returns:
            Configured PolymarketDataClient
        """
        if self._data_client is not None:
            logger.debug("Using cached Data API client")
            return self._data_client

        logger.info("Creating Data API client...")
        data_client = PolymarketDataClient()

        # Attach shared HTTP clients (proxy/verify settings handled centrally)
        data_client.client = self._get_http_client()
        try:
            # If SDK supports async client, attach it as well
            data_client.async_client = self._get_async_http_client()  # type: ignore[attr-defined]
        except Exception:
            pass

        self._data_client = data_client
        logger.info("Data API client created")
        return data_client

    def get_legacy_clob_client(self) -> LegacyClobClient:
        """Get a shared legacy py_clob_client.ClobClient (read-only usage)."""
        if self._legacy_clob_client is not None:
            logger.debug("Using cached legacy CLOB client")
            return self._legacy_clob_client

        self._apply_requests_defaults()

        self._legacy_clob_client = LegacyClobClient(
            host="https://clob.polymarket.com",
            chain_id=137,
        )
        logger.info("Legacy CLOB client created")
        return self._legacy_clob_client

    def _apply_requests_defaults(self) -> None:
        """Ensure requests respects factory proxy/SSL settings for legacy clients."""
        if self._requests_defaults_applied:
            return

        verify_ssl = self.api_config.get('verify_ssl', True)
        proxy = self.api_config.get('proxy')
        timeout = self.api_config.get('timeout', 30.0)

        original_request = requests.Session.request

        proxies_dict = None
        if proxy:
            proxies_dict = {
                "http": proxy,
                "https": proxy,
            }

        def patched_request(session, method, url, **kwargs):
            if not verify_ssl:
                kwargs.setdefault('verify', False)
            if proxies_dict is not None and 'proxies' not in kwargs:
                kwargs['proxies'] = proxies_dict
            if timeout is not None and 'timeout' not in kwargs:
                kwargs['timeout'] = timeout
            return original_request(session, method, url, **kwargs)

        requests.Session.request = patched_request
        self._original_requests_method = original_request
        self._requests_defaults_applied = True

        if not verify_ssl:
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except ImportError:
                pass

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
            self._data_client = None
            self._legacy_clob_client = None
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

        if self._requests_defaults_applied and self._original_requests_method:
            requests.Session.request = self._original_requests_method
            self._original_requests_method = None
            self._requests_defaults_applied = False

        logger.info("ClientFactory closed")




