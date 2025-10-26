"""
Wallet management service.

Provides functionality for managing and querying wallet information.
Note: This service is now primarily a wrapper around WalletManager.
Consider using WalletManager directly in most cases.
"""

from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
import logging

from py_clob_client.client import ClobClient as LegacyClobClient
from py_clob_client.clob_types import BalanceAllowanceParams
from web3 import Web3

from poly_boost.core.wallet import Wallet
from poly_boost.core.wallet_manager import WalletManager
from poly_boost.core.client_factory import ClientFactory


logger = logging.getLogger(__name__)

# USDC contract address on Polygon
USDC_CONTRACT_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"

# Minimal ERC20 ABI for balanceOf
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    }
]


class WalletService:
    """
    Service for managing wallet information.

    Note: This service is now a thin wrapper around WalletManager.
    For new code, consider using WalletManager directly.
    """

    def __init__(
        self,
        clob_client: LegacyClobClient,
        wallet_manager: Optional[WalletManager] = None,
        client_factory: Optional[ClientFactory] = None,
        polygon_rpc_url: str = "https://polygon-rpc.com"
    ):
        """
        Initialize wallet service.

        Args:
            clob_client: Legacy py_clob_client.ClobClient instance (for backward compatibility)
            wallet_manager: Optional WalletManager instance
            client_factory: Optional ClientFactory for creating wallet-specific clients
            polygon_rpc_url: Polygon RPC URL for on-chain balance queries
        """
        self.clob_client = clob_client
        self.wallet_manager = wallet_manager or WalletManager()
        self.client_factory = client_factory

        # Cache for wallet-specific legacy clients (for balance queries)
        self._legacy_client_cache: Dict[str, LegacyClobClient] = {}

        # Web3 instance for on-chain queries (for ReadOnly wallets)
        self.web3 = Web3(Web3.HTTPProvider(polygon_rpc_url))
        self.usdc_contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(USDC_CONTRACT_ADDRESS),
            abi=ERC20_ABI
        )

    def register_wallet(self, wallet: Wallet) -> str:
        """
        Register a wallet for management.

        Args:
            wallet: Wallet instance

        Returns:
            Wallet api_address
        """
        self.wallet_manager.register(wallet)
        return wallet.api_address

    def get_wallet_info(self, wallet_address: str) -> Dict[str, Any]:
        """
        Get information about a wallet.

        Args:
            wallet_address: Wallet address (api_address or eoa_address)

        Returns:
            Wallet information dictionary
        """
        wallet = self.wallet_manager.get(wallet_address)

        if wallet is None:
            # Return info for unmanaged wallet
            return {
                "address": wallet_address,
                "name": "Unknown",
                "is_managed": False
            }

        # Import ProxyWallet for type checking
        from poly_boost.core.wallet import ProxyWallet

        info = {
            "address": wallet.api_address,
            "eoa_address": wallet.eoa_address,
            "name": wallet.name,
            "signature_type": wallet.signature_type,
            "is_managed": True,
            "is_tradable": wallet.requires_private_key
        }

        # Add proxy_address if it's a proxy wallet
        if isinstance(wallet, ProxyWallet):
            info["proxy_address"] = wallet.proxy_address

        return info

    def get_balance(self, wallet: Union[Wallet, str]) -> Decimal:
        """
        Get USDC balance for a wallet.

        Args:
            wallet: Wallet instance or wallet address string

        Returns:
            USDC balance (in USDC, not raw units)

        Raises:
            ValueError: If wallet not found
            Exception: If balance query fails
        """
        try:
            # Support both Wallet objects and address strings
            if isinstance(wallet, Wallet):
                wallet_obj = wallet
            else:
                # Resolve wallet from manager
                wallet_obj = self.wallet_manager.get(wallet)
                if wallet_obj is None:
                    raise ValueError(f"Wallet not found: {wallet}")

            address = wallet_obj.api_address
            wallet_name = wallet_obj.name
            signature_type = wallet_obj.signature_type

            logger.info(f"Fetching balance for wallet: {wallet_name} ({address})")

            # For ReadOnly wallets, query on-chain balance directly
            if not wallet_obj.requires_private_key:
                logger.info(f"Wallet '{wallet_name}' is read-only, querying on-chain balance")
                return self._get_onchain_balance(address, wallet_name)

            # For wallets with private keys, use API
            # Get or create wallet-specific legacy CLOB client
            legacy_client = self._get_legacy_clob_client(wallet_obj)

            # Query USDC balance using legacy client
            sig_type = 0 if signature_type == -1 else signature_type

            params = BalanceAllowanceParams(
                asset_type="COLLATERAL",  # COLLATERAL = USDC
                signature_type=sig_type
            )

            result = legacy_client.get_balance_allowance(params)

            # Extract balance (USDC uses 6 decimal places)
            balance_raw = result.get('balance', '0')

            # Convert to Decimal (divide by 10^6)
            balance = Decimal(str(balance_raw)) / Decimal('1000000')

            logger.info(f"Balance for {wallet_name}: {balance} USDC")
            return balance

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch balance: {e}", exc_info=True)
            raise

    def _get_onchain_balance(self, address: str, wallet_name: str = "") -> Decimal:
        """
        Query USDC balance directly from blockchain.

        Args:
            address: Wallet address
            wallet_name: Wallet name for logging

        Returns:
            USDC balance

        Raises:
            Exception: If query fails
        """
        try:
            checksum_address = Web3.to_checksum_address(address)
            balance_raw = self.usdc_contract.functions.balanceOf(checksum_address).call()

            # USDC uses 6 decimal places
            balance = Decimal(str(balance_raw)) / Decimal('1000000')

            logger.info(f"On-chain balance for {wallet_name or address}: {balance} USDC")
            return balance

        except Exception as e:
            logger.error(f"Failed to query on-chain balance: {e}", exc_info=True)
            raise

    def _get_legacy_clob_client(self, wallet: Wallet) -> LegacyClobClient:
        """
        Get or create a legacy py_clob_client.ClobClient for a wallet.

        Args:
            wallet: Wallet instance

        Returns:
            Legacy ClobClient instance with API credentials

        Raises:
            ValueError: If wallet is read-only or private key not available
        """
        cache_key = wallet.api_address.lower()

        # Return cached client if available
        if cache_key in self._legacy_client_cache:
            logger.debug(f"Using cached legacy client for wallet '{wallet.name}'")
            return self._legacy_client_cache[cache_key]

        # Validate wallet
        if not wallet.requires_private_key:
            raise ValueError(
                f"Wallet '{wallet.name}' is read-only, cannot query balance without credentials"
            )

        private_key = wallet.get_private_key()
        if not private_key:
            raise ValueError(
                f"Private key not available for wallet '{wallet.name}'. "
                f"Please set the required environment variable."
            )

        logger.info(f"Creating legacy CLOB client for wallet '{wallet.name}'...")

        # Import ProxyWallet for type checking
        from poly_boost.core.wallet import ProxyWallet

        # Determine client parameters based on wallet type
        client_params = {
            'host': 'https://clob.polymarket.com',
            'key': private_key,
            'chain_id': 137,
            'signature_type': wallet.signature_type,
        }

        # If proxy wallet, specify funder address
        if isinstance(wallet, ProxyWallet):
            client_params['funder'] = wallet.proxy_address
            logger.debug(
                f"Proxy wallet detected: EOA={wallet.eoa_address}, "
                f"Proxy={wallet.proxy_address}"
            )

        # Create legacy client
        legacy_client = LegacyClobClient(**client_params)

        # Create or derive API credentials
        try:
            creds = legacy_client.create_or_derive_api_creds()
            legacy_client.set_api_creds(creds)
            logger.info(f"API credentials set for legacy client '{wallet.name}'")
        except Exception as e:
            logger.warning(f"Failed to set API credentials: {e}")
            # Continue anyway - some operations might still work

        # Cache and return
        self._legacy_client_cache[cache_key] = legacy_client
        logger.info(f"Legacy CLOB client created for wallet '{wallet.name}'")

        return legacy_client

    def list_managed_wallets(self) -> List[Dict[str, Any]]:
        """
        List all managed wallets.

        Returns:
            List of wallet information dictionaries
        """
        return [
            self.get_wallet_info(wallet.api_address)
            for wallet in self.wallet_manager.list_all()
        ]
