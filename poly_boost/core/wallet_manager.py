"""
WalletManager - Central wallet registry.

Manages all wallets in the application and provides unified access interface.
"""

from typing import Dict, List, Optional
from poly_boost.core.wallet import Wallet, EOAWallet, ProxyWallet, ReadOnlyWallet
import logging

logger = logging.getLogger(__name__)


class WalletManager:
    """
    Central wallet manager.

    Responsibilities:
    1. Load all wallets from configuration
    2. Provide unified wallet lookup interface
    3. Manage wallet lifecycle

    Wallets are indexed by api_address (the address used for API calls),
    with additional indexing by eoa_address for convenience.
    """

    def __init__(self):
        """Initialize empty wallet manager."""
        # Primary index: api_address -> Wallet
        # This is the address used when calling Polymarket APIs
        self._wallets: Dict[str, Wallet] = {}

        # Secondary index: eoa_address -> Wallet
        # Allows finding proxy wallets by their EOA address
        self._eoa_to_wallet: Dict[str, Wallet] = {}

    def register(self, wallet: Wallet) -> None:
        """
        Register a wallet to the manager.

        Args:
            wallet: Wallet instance to register
        """
        api_addr_lower = wallet.api_address.lower()
        eoa_addr_lower = wallet.eoa_address.lower()

        # Check for duplicate api_address
        if api_addr_lower in self._wallets:
            existing = self._wallets[api_addr_lower]
            logger.warning(
                f"Wallet with api_address {wallet.api_address} already registered "
                f"(existing: '{existing.name}', new: '{wallet.name}'). Replacing."
            )

        # Register in both indexes
        self._wallets[api_addr_lower] = wallet
        self._eoa_to_wallet[eoa_addr_lower] = wallet

        logger.info(
            f"Registered wallet: '{wallet.name}' "
            f"(api_address={wallet.api_address}, signature_type={wallet.signature_type})"
        )

    def get(self, identifier: str) -> Optional[Wallet]:
        """
        Get wallet by identifier (smart lookup).

        The identifier can be:
        - EOA address
        - Proxy address
        - Wallet name

        This method iterates through all registered wallets and uses each wallet's
        matches_identifier() method to find a match. This ensures that the correct
        wallet is found regardless of which address format the user provides.

        Args:
            identifier: Address or name to lookup (case-insensitive)

        Returns:
            Wallet instance if found, None otherwise
        """
        # Fast path: try api_address first (most common case)
        identifier_lower = identifier.lower()
        wallet = self._wallets.get(identifier_lower)
        if wallet:
            return wallet

        # Slow path: iterate through all wallets and check if any matches
        for wallet in self._wallets.values():
            if wallet.matches_identifier(identifier):
                return wallet

        return None

    def get_or_raise(self, address: str) -> Wallet:
        """
        Get wallet by address, raise exception if not found.

        Args:
            address: Address to lookup

        Returns:
            Wallet instance

        Raises:
            ValueError: If wallet not found
        """
        wallet = self.get(address)
        if wallet is None:
            available = ', '.join(self._wallets.keys())
            raise ValueError(
                f"Wallet with address '{address}' not found. "
                f"Available wallets: [{available}]"
            )
        return wallet

    def list_all(self) -> List[Wallet]:
        """
        Get all registered wallets.

        Returns:
            List of all Wallet instances
        """
        return list(self._wallets.values())

    def list_tradable(self) -> List[Wallet]:
        """
        Get all tradable wallets (those with private keys).

        Returns:
            List of wallets that can execute transactions
        """
        return [w for w in self._wallets.values() if w.requires_private_key]

    def list_readonly(self) -> List[Wallet]:
        """
        Get all read-only wallets.

        Returns:
            List of wallets that can only query data
        """
        return [w for w in self._wallets.values() if not w.requires_private_key]

    def get_by_name(self, name: str) -> Optional[Wallet]:
        """
        Get wallet by name.

        Args:
            name: Wallet name

        Returns:
            Wallet instance if found, None otherwise
        """
        for wallet in self._wallets.values():
            if wallet.name == name:
                return wallet
        return None

    @classmethod
    def from_config(cls, config: dict) -> 'WalletManager':
        """
        Create WalletManager from configuration dictionary.

        Expected config structure:
        {
            "user_wallets": [
                {
                    "name": "My Wallet",
                    "address": "0x...",
                    "signature_type": 0,  # or 1, 2
                    "private_key_env": "WALLET_PRIVATE_KEY",
                    "proxy_address": "0x..."  # required if signature_type != 0
                }
            ],
            "watch_wallets": [
                {
                    "name": "Watched Trader",
                    "address": "0x..."
                }
            ]
        }

        Args:
            config: Configuration dictionary

        Returns:
            Initialized WalletManager instance

        Raises:
            ValueError: If configuration is invalid
        """
        manager = cls()

        # Load user wallets (tradable)
        user_wallets = config.get('user_wallets', [])
        logger.info(f"Loading {len(user_wallets)} user wallets...")

        for wallet_config in user_wallets:
            try:
                wallet = cls._create_wallet_from_config(wallet_config)
                manager.register(wallet)
            except Exception as e:
                wallet_name = wallet_config.get('name', 'Unknown')
                logger.error(f"Failed to load user wallet '{wallet_name}': {e}")
                raise

        # Load watch wallets (read-only)
        watch_wallets = config.get('watch_wallets', [])
        logger.info(f"Loading {len(watch_wallets)} watch wallets...")

        for wallet_config in watch_wallets:
            try:
                wallet = ReadOnlyWallet(
                    name=wallet_config.get('name', 'Unknown'),
                    address=wallet_config['address']
                )
                manager.register(wallet)
            except Exception as e:
                wallet_name = wallet_config.get('name', 'Unknown')
                logger.error(f"Failed to load watch wallet '{wallet_name}': {e}")
                raise

        logger.info(
            f"WalletManager initialized: {len(manager.list_tradable())} tradable, "
            f"{len(manager.list_readonly())} read-only"
        )

        return manager

    @staticmethod
    def _create_wallet_from_config(config: dict) -> Wallet:
        """
        Create Wallet instance from configuration dictionary.

        Args:
            config: Wallet configuration

        Returns:
            Wallet instance (EOAWallet or ProxyWallet)

        Raises:
            ValueError: If configuration is invalid
        """
        name = config.get('name', 'Unknown')
        address = config.get('address')
        signature_type = config.get('signature_type', 2)
        private_key_env = config.get('private_key_env')

        if not address:
            raise ValueError(f"Wallet '{name}' missing required field: address")

        if signature_type == 0:
            # EOA wallet
            return EOAWallet(
                name=name,
                address=address,
                private_key_env=private_key_env
            )
        else:
            # Proxy wallet (signature_type 1 or 2)
            proxy_address = config.get('proxy_address')
            if not proxy_address:
                raise ValueError(
                    f"Wallet '{name}' with signature_type={signature_type} "
                    f"requires proxy_address"
                )

            if not private_key_env:
                raise ValueError(
                    f"Wallet '{name}' requires private_key_env for trading operations"
                )

            return ProxyWallet(
                name=name,
                eoa_address=address,
                proxy_address=proxy_address,
                private_key_env=private_key_env,
                signature_type=signature_type
            )
