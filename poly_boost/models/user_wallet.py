"""
User wallet association model for Telegram bot users.

Maps Telegram user IDs to Ethereum wallet credentials.
Private keys stored in plaintext per FR-019 with strict access controls.
"""

from datetime import datetime
from peewee import Model, BigIntegerField, CharField, IntegerField, DateTimeField
from poly_boost.core.models import db


class UserWallet(Model):
    """
    User wallet association for Telegram bot users.

    Maps Telegram user IDs to Ethereum wallet credentials.
    Private keys stored in plaintext per FR-019 with strict access controls.
    """

    telegram_user_id = BigIntegerField(primary_key=True, index=True)
    """
    Telegram user ID (64-bit integer).
    Primary key to ensure one wallet per user.
    Indexed for fast lookups.
    """

    wallet_address = CharField(max_length=42, unique=True, index=True)
    """
    Ethereum wallet address (checksum format).
    Format: 0x + 40 hexadecimal characters (42 total).
    Unique constraint prevents duplicate wallets.
    Indexed for reverse lookups (wallet → user).
    """

    private_key = CharField(max_length=66)
    """
    Ethereum private key (plaintext per FR-019).
    Format: 0x + 64 hexadecimal characters (66 total).
    NOT indexed (would leak information about key distribution).
    NOT encrypted in v1 (access controls are security boundary).
    """

    wallet_name = CharField(max_length=100, null=True)
    """
    Optional user-defined wallet nickname.
    Default: None (display as "Wallet {telegram_user_id}").
    """

    signature_type = IntegerField(default=0)
    """
    Wallet signature type for future extensibility.
    Values:
      0 = EOA (Externally Owned Account) - standard private key
      1 = AA (Account Abstraction) - future support for smart contract wallets
    Default: 0 (EOA).
    """

    created_at = DateTimeField(default=datetime.now)
    """
    Timestamp when wallet was first associated.
    Immutable after creation.
    """

    updated_at = DateTimeField(default=datetime.now)
    """
    Timestamp of last update (e.g., wallet_name changed).
    Auto-updated on save.
    """

    class Meta:
        database = db
        table_name = 'user_wallets'
        indexes = (
            (('telegram_user_id',), True),  # Unique index (primary key)
            (('wallet_address',), True),    # Unique index
        )

    def to_wallet(self):
        """
        Convert to poly_boost.core.wallet.EOAWallet for use with services.

        Returns:
            EOAWallet: Wallet object for trading operations.
        """
        from poly_boost.core.wallet import EOAWallet

        # Create EOAWallet without environment variable for private key
        # Instead, we'll directly set the private key
        wallet = EOAWallet(
            name=self.wallet_name or f"Wallet_{self.telegram_user_id}",
            address=self.wallet_address,
            private_key_env=None
        )
        # Directly set the private key
        wallet._private_key = self.private_key
        return wallet

    def save(self, *args, **kwargs):
        """Override save to update updated_at timestamp."""
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)
