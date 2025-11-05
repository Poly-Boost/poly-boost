"""
Service for managing user wallet associations.

Provides CRUD operations for linking Telegram users to Ethereum wallets.
All business logic for wallet initialization, retrieval, and updates
is centralized here.
"""

import logging
from typing import Optional
from datetime import datetime

from web3 import Web3
from eth_account import Account
from peewee import IntegrityError, DoesNotExist

from poly_boost.models.user_wallet import UserWallet
from poly_boost.core.wallet import EOAWallet

logger = logging.getLogger(__name__)


class UserWalletService:
    """
    Service for managing user wallet associations.

    Provides CRUD operations for linking Telegram users to Ethereum wallets.
    All business logic for wallet initialization, retrieval, and updates
    is centralized here.

    Thread-safe: Database operations use peewee ORM connection pooling.
    """

    def __init__(self, database=None):
        """
        Initialize the service with database connection.

        Args:
            database: Peewee Database instance (PostgreSQL or SQLite).
                     If None, uses the default database from models.
        """
        self.database = database

    def create_user_wallet(
        self,
        telegram_user_id: int,
        wallet_address: str,
        private_key: str,
        wallet_name: Optional[str] = None,
        signature_type: int = 0
    ) -> UserWallet:
        """
        Create a new user wallet association.

        Args:
            telegram_user_id: Telegram user ID (64-bit integer).
            wallet_address: Ethereum wallet address (0x + 40 hex chars).
            private_key: Ethereum private key (0x + 64 hex chars).
            wallet_name: Optional user-defined wallet nickname (max 100 chars).
            signature_type: Wallet signature type (0=EOA, 1=AA). Default: 0.

        Returns:
            UserWallet: Created user wallet record.

        Raises:
            ValueError: If validation fails (invalid address/key format).
            IntegrityError: If telegram_user_id or wallet_address already exists.

        Example:
            >>> service = UserWalletService(database)
            >>> wallet = service.create_user_wallet(
            ...     telegram_user_id=123456789,
            ...     wallet_address="0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B",
            ...     private_key="0x" + "a" * 64,
            ...     wallet_name="My Trading Wallet"
            ... )
            >>> assert wallet.telegram_user_id == 123456789
        """
        # Validate wallet address checksum
        if not self._validate_wallet_address(wallet_address):
            logger.error(
                "Invalid wallet address format",
                extra={
                    "telegram_user_id": telegram_user_id,
                    "wallet_address": wallet_address
                }
            )
            raise ValueError("Invalid wallet address")

        # Validate private key and ensure it matches address
        is_valid, derived_address = self._validate_private_key(private_key)
        if not is_valid:
            logger.error(
                "Invalid private key format",
                extra={"telegram_user_id": telegram_user_id}
            )
            raise ValueError("Invalid private key")

        # Ensure private key derives the same address
        if derived_address.lower() != wallet_address.lower():
            logger.error(
                "Private key does not match wallet address",
                extra={
                    "telegram_user_id": telegram_user_id,
                    "expected_address": wallet_address,
                    "derived_address": derived_address
                }
            )
            raise ValueError("Private key does not match address")

        # Validate wallet name length
        if wallet_name and len(wallet_name) > 100:
            raise ValueError("Wallet name too long (max 100 characters)")

        # Validate signature type
        if signature_type not in [0, 1]:
            raise ValueError("Invalid signature type (must be 0 or 1)")

        try:
            # Create user wallet record
            user_wallet = UserWallet.create(
                telegram_user_id=telegram_user_id,
                wallet_address=Web3.to_checksum_address(wallet_address),
                private_key=private_key,
                wallet_name=wallet_name,
                signature_type=signature_type
            )

            logger.info(
                "Created wallet for user",
                extra={
                    "telegram_user_id": telegram_user_id,
                    "wallet_address": user_wallet.wallet_address
                }
            )

            return user_wallet

        except IntegrityError as e:
            # Check which constraint was violated
            error_str = str(e).lower()
            if "telegram_user_id" in error_str or "primary key" in error_str:
                logger.warning(
                    "User already has a wallet",
                    extra={"telegram_user_id": telegram_user_id}
                )
                raise IntegrityError("User already has a wallet")
            elif "wallet_address" in error_str or "unique" in error_str:
                logger.warning(
                    "Wallet address already registered",
                    extra={
                        "telegram_user_id": telegram_user_id,
                        "wallet_address": wallet_address
                    }
                )
                raise IntegrityError("Wallet address already registered")
            else:
                # Re-raise original error if we can't determine the cause
                raise

    def get_user_wallet(self, telegram_user_id: int) -> Optional[UserWallet]:
        """
        Retrieve user wallet by Telegram user ID.

        Args:
            telegram_user_id: Telegram user ID to look up.

        Returns:
            UserWallet if found, None if user has no wallet.

        Example:
            >>> service = UserWalletService(database)
            >>> wallet = service.get_user_wallet(123456789)
            >>> if wallet:
            ...     print(f"Address: {wallet.wallet_address}")
            ... else:
            ...     print("User has no wallet")
        """
        try:
            wallet = UserWallet.get(UserWallet.telegram_user_id == telegram_user_id)
            return wallet
        except DoesNotExist:
            return None

    def get_user_wallet_by_address(self, wallet_address: str) -> Optional[UserWallet]:
        """
        Retrieve user wallet by Ethereum address (reverse lookup).

        Args:
            wallet_address: Ethereum wallet address to look up.

        Returns:
            UserWallet if found, None if address not registered.

        Example:
            >>> service = UserWalletService(database)
            >>> wallet = service.get_user_wallet_by_address(
            ...     "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B"
            ... )
            >>> if wallet:
            ...     print(f"Telegram User ID: {wallet.telegram_user_id}")
        """
        try:
            # Normalize to checksum address for case-insensitive comparison
            checksum_address = Web3.to_checksum_address(wallet_address)
            wallet = UserWallet.get(UserWallet.wallet_address == checksum_address)
            return wallet
        except (DoesNotExist, ValueError):
            # ValueError can be raised by to_checksum_address if invalid format
            return None

    def update_user_wallet(
        self,
        telegram_user_id: int,
        wallet_name: Optional[str] = None
    ) -> UserWallet:
        """
        Update user wallet information.

        Currently supports updating wallet_name only.
        Private key and address updates not supported (security risk).

        Args:
            telegram_user_id: Telegram user ID of wallet to update.
            wallet_name: New wallet nickname (None to clear, max 100 chars).

        Returns:
            Updated UserWallet record.

        Raises:
            ValueError: If wallet_name > 100 characters.
            DoesNotExist: If telegram_user_id has no wallet.

        Example:
            >>> service = UserWalletService(database)
            >>> wallet = service.update_user_wallet(
            ...     telegram_user_id=123456789,
            ...     wallet_name="Updated Name"
            ... )
            >>> assert wallet.wallet_name == "Updated Name"
        """
        # Validate wallet name length
        if wallet_name and len(wallet_name) > 100:
            raise ValueError("Wallet name too long (max 100 characters)")

        try:
            # Get existing wallet
            wallet = UserWallet.get(UserWallet.telegram_user_id == telegram_user_id)

            # Update wallet name
            wallet.wallet_name = wallet_name
            wallet.save()

            logger.info(
                "Updated wallet name",
                extra={
                    "telegram_user_id": telegram_user_id,
                    "wallet_name": wallet_name
                }
            )

            return wallet

        except DoesNotExist:
            logger.error(
                "Wallet not found for update",
                extra={"telegram_user_id": telegram_user_id}
            )
            raise DoesNotExist(f"No wallet found for user {telegram_user_id}")

    def delete_user_wallet(self, telegram_user_id: int) -> bool:
        """
        Delete user wallet (admin operation, future feature).

        WARNING: Irreversible operation. User loses access to wallet credentials.
        Not exposed to end users in v1.

        Args:
            telegram_user_id: Telegram user ID of wallet to delete.

        Returns:
            True if wallet was deleted, False if wallet didn't exist.

        Example:
            >>> service = UserWalletService(database)
            >>> deleted = service.delete_user_wallet(123456789)
            >>> if deleted:
            ...     print("Wallet deleted")
            ... else:
            ...     print("Wallet didn't exist")
        """
        try:
            wallet = UserWallet.get(UserWallet.telegram_user_id == telegram_user_id)
            wallet.delete_instance()

            logger.warning(
                "Deleted user wallet",
                extra={
                    "telegram_user_id": telegram_user_id,
                    "wallet_address": wallet.wallet_address
                }
            )

            return True

        except DoesNotExist:
            return False

    def wallet_exists(self, telegram_user_id: int) -> bool:
        """
        Check if user has a wallet registered.

        Args:
            telegram_user_id: Telegram user ID to check.

        Returns:
            True if user has a wallet, False otherwise.

        Example:
            >>> service = UserWalletService(database)
            >>> if not service.wallet_exists(123456789):
            ...     print("Please initialize wallet with /start")
        """
        return UserWallet.select().where(
            UserWallet.telegram_user_id == telegram_user_id
        ).exists()

    @staticmethod
    def _validate_wallet_address(address: str) -> bool:
        """
        Validate Ethereum address format and checksum.

        Args:
            address: Ethereum address to validate

        Returns:
            True if valid checksum address, False otherwise
        """
        if not address or len(address) != 42:
            return False
        if not address.startswith('0x'):
            return False
        try:
            # web3.py checksum validation
            return Web3.is_checksum_address(address)
        except Exception:
            return False

    @staticmethod
    def _validate_private_key(private_key: str) -> tuple[bool, Optional[str]]:
        """
        Validate private key format and derive address.

        Args:
            private_key: Private key to validate

        Returns:
            Tuple of (is_valid, derived_address or None)
        """
        if not private_key or len(private_key) != 66:
            return False, None
        if not private_key.startswith('0x'):
            return False, None
        try:
            # Attempt to create account from private key
            account = Account.from_key(private_key)
            return True, account.address
        except Exception:
            return False, None
