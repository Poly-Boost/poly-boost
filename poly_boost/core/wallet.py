"""
Wallet abstraction layer.

Provides unified interface for different wallet types (EOA, Proxy, ReadOnly).
All services use wallet.api_address to call APIs, abstracting away wallet type differences.
"""

from abc import ABC, abstractmethod
from typing import Optional
from web3 import Web3
import os
import logging

logger = logging.getLogger(__name__)


class Wallet(ABC):
    """
    Abstract base class for all wallet types.

    Encapsulates the differences between wallet types and provides a unified interface.
    The key abstraction is `api_address` - the address to use when calling Polymarket APIs.
    """

    def __init__(self, name: str, eoa_address: str):
        """
        Initialize wallet.

        Args:
            name: Human-readable wallet name
            eoa_address: EOA (Externally Owned Account) address
        """
        self.name = name
        self.eoa_address = Web3.to_checksum_address(eoa_address)

    @property
    @abstractmethod
    def api_address(self) -> str:
        """
        Get the address to use when calling Polymarket APIs.

        This is the core abstraction that hides wallet type differences:
        - EOA wallets: returns eoa_address
        - Proxy wallets: returns proxy_address
        - ReadOnly wallets: returns the watched address

        Returns:
            Checksum address to use for API calls
        """
        pass

    @property
    @abstractmethod
    def signature_type(self) -> int:
        """
        Get the signature type for this wallet.

        Returns:
            0 for EOA, 1 for Proxy, 2 for Gnosis Safe, -1 for ReadOnly
        """
        pass

    @property
    @abstractmethod
    def requires_private_key(self) -> bool:
        """
        Check if this wallet requires a private key.

        Returns:
            True if wallet can execute transactions, False if read-only
        """
        pass

    @abstractmethod
    def get_private_key(self) -> Optional[str]:
        """
        Get the private key for this wallet.

        Returns:
            Private key string, or None if not available/applicable
        """
        pass

    @abstractmethod
    def matches_identifier(self, identifier: str) -> bool:
        """
        Check if this wallet matches the given identifier.

        The identifier could be:
        - EOA address
        - Proxy address
        - Wallet name

        Args:
            identifier: Address or name to match (case-insensitive)

        Returns:
            True if this wallet matches the identifier
        """
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__} name='{self.name}' api_address={self.api_address}>"

    def __str__(self):
        return f"{self.name} ({self.api_address})"


class EOAWallet(Wallet):
    """
    EOA (Externally Owned Account) wallet.

    Direct wallet without proxy. Uses the original address for all operations.
    """

    def __init__(self, name: str, address: str, private_key_env: Optional[str] = None):
        """
        Initialize EOA wallet.

        Args:
            name: Wallet name
            address: EOA address
            private_key_env: Environment variable name containing private key (optional)
        """
        super().__init__(name, address)
        self._private_key_env = private_key_env
        self._private_key: Optional[str] = None

        # Load private key from environment if configured
        if private_key_env:
            self._private_key = os.getenv(private_key_env)
            if not self._private_key:
                logger.warning(
                    f"Private key environment variable '{private_key_env}' "
                    f"not set for wallet '{name}'"
                )

    @property
    def api_address(self) -> str:
        """EOA wallets use the original address directly."""
        return self.eoa_address

    @property
    def signature_type(self) -> int:
        return 0

    @property
    def requires_private_key(self) -> bool:
        return self._private_key_env is not None

    def get_private_key(self) -> Optional[str]:
        return self._private_key

    def matches_identifier(self, identifier: str) -> bool:
        """
        EOA wallet matches:
        - Its EOA address (case-insensitive)
        - Its wallet name (case-insensitive)
        """
        identifier_lower = identifier.lower()
        return (
            self.eoa_address.lower() == identifier_lower or
            self.name.lower() == identifier_lower
        )


class ProxyWallet(Wallet):
    """
    Proxy wallet (signature_type=1 or 2).

    Uses a proxy contract for operations. API calls use the proxy address.
    """

    def __init__(
        self,
        name: str,
        eoa_address: str,
        proxy_address: str,
        private_key_env: str,
        signature_type: int = 2  # Default to Gnosis Safe
    ):
        """
        Initialize proxy wallet.

        Args:
            name: Wallet name
            eoa_address: EOA address (owner)
            proxy_address: Proxy contract address
            private_key_env: Environment variable name containing private key
            signature_type: 1 for Proxy, 2 for Gnosis Safe

        Raises:
            ValueError: If signature_type is invalid
        """
        super().__init__(name, eoa_address)
        self.proxy_address = Web3.to_checksum_address(proxy_address)
        self._signature_type = signature_type
        self._private_key_env = private_key_env
        self._private_key: Optional[str] = None

        if signature_type not in [1, 2]:
            raise ValueError(
                f"Invalid signature_type for ProxyWallet: {signature_type}. "
                f"Must be 1 (Proxy) or 2 (Gnosis Safe)"
            )

        # Load private key from environment
        self._private_key = os.getenv(private_key_env)
        if not self._private_key:
            logger.warning(
                f"Private key environment variable '{private_key_env}' "
                f"not set for wallet '{name}'"
            )

    @property
    def api_address(self) -> str:
        """Proxy wallets use the proxy contract address."""
        return self.proxy_address

    @property
    def signature_type(self) -> int:
        return self._signature_type

    @property
    def requires_private_key(self) -> bool:
        return True

    def get_private_key(self) -> Optional[str]:
        return self._private_key

    def matches_identifier(self, identifier: str) -> bool:
        """
        Proxy wallet matches:
        - Its EOA address (case-insensitive)
        - Its proxy address (case-insensitive)
        - Its wallet name (case-insensitive)
        """
        identifier_lower = identifier.lower()
        return (
            self.eoa_address.lower() == identifier_lower or
            self.proxy_address.lower() == identifier_lower or
            self.name.lower() == identifier_lower
        )


class ReadOnlyWallet(Wallet):
    """
    Read-only wallet for monitoring other addresses.

    Cannot execute transactions, only query data.
    """

    def __init__(self, name: str, address: str):
        """
        Initialize read-only wallet.

        Args:
            name: Wallet name
            address: Address to monitor
        """
        super().__init__(name, address)

    @property
    def api_address(self) -> str:
        """Read-only wallets use the monitored address."""
        return self.eoa_address

    @property
    def signature_type(self) -> int:
        return -1  # Special marker for read-only

    @property
    def requires_private_key(self) -> bool:
        return False

    def get_private_key(self) -> Optional[str]:
        return None

    def matches_identifier(self, identifier: str) -> bool:
        """
        ReadOnly wallet matches:
        - Its address (case-insensitive)
        - Its wallet name (case-insensitive)
        """
        identifier_lower = identifier.lower()
        return (
            self.eoa_address.lower() == identifier_lower or
            self.name.lower() == identifier_lower
        )
