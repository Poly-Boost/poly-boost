# UserWalletService Contract

**Module**: `poly_boost.services.user_wallet_service`
**Purpose**: Manage user-wallet associations for Telegram bot users
**Pattern**: CRUD service layer following Service-First Architecture

## Class Definition

```python
from typing import Optional
from datetime import datetime

from poly_boost.models.user_wallet import UserWallet
from poly_boost.core.wallet import Wallet


class UserWalletService:
    """
    Service for managing user wallet associations.

    Provides CRUD operations for linking Telegram users to Ethereum wallets.
    All business logic for wallet initialization, retrieval, and updates
    is centralized here.

    Thread-safe: Database operations use peewee ORM connection pooling.
    """

    def __init__(self, database):
        """
        Initialize the service with database connection.

        Args:
            database: Peewee Database instance (PostgreSQL or SQLite).
        """
        self.database = database
```

## Interface Methods

### 1. create_user_wallet

**Signature**:
```python
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
        DatabaseError: If database operation fails.

    Preconditions:
        - telegram_user_id must be positive 64-bit integer
        - wallet_address must pass checksum validation
        - private_key must be valid and derive wallet_address
        - wallet_name must be ≤100 characters if provided
        - signature_type must be 0 or 1

    Postconditions:
        - User wallet record created in database
        - created_at and updated_at timestamps set to current time
        - Returns fully populated UserWallet instance

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
```

**Business Rules**:
- Validates wallet address checksum (web3.py `is_checksum_address`)
- Validates private key format and derives address
- Ensures derived address matches provided wallet_address
- Enforces unique constraint on telegram_user_id (one wallet per user)
- Enforces unique constraint on wallet_address (no duplicate wallets)

**Error Handling**:
| Error Type | Condition | Action |
|------------|-----------|--------|
| ValueError | Invalid address format | Raise with message "Invalid wallet address" |
| ValueError | Invalid private key format | Raise with message "Invalid private key" |
| ValueError | Private key doesn't match address | Raise with message "Private key does not match address" |
| ValueError | wallet_name > 100 chars | Raise with message "Wallet name too long" |
| IntegrityError | Duplicate telegram_user_id | Raise with message "User already has a wallet" |
| IntegrityError | Duplicate wallet_address | Raise with message "Wallet address already registered" |

---

### 2. get_user_wallet

**Signature**:
```python
def get_user_wallet(self, telegram_user_id: int) -> Optional[UserWallet]:
    """
    Retrieve user wallet by Telegram user ID.

    Args:
        telegram_user_id: Telegram user ID to look up.

    Returns:
        UserWallet if found, None if user has no wallet.

    Raises:
        DatabaseError: If database query fails.

    Preconditions:
        - telegram_user_id must be provided

    Postconditions:
        - Returns UserWallet with all fields populated if found
        - Returns None if not found (not an error condition)
        - No side effects (read-only operation)

    Example:
        >>> service = UserWalletService(database)
        >>> wallet = service.get_user_wallet(123456789)
        >>> if wallet:
        ...     print(f"Address: {wallet.wallet_address}")
        ... else:
        ...     print("User has no wallet")
    """
```

**Business Rules**:
- Lookup by primary key (fast indexed query)
- Returns None if not found (caller decides how to handle)
- No caching (always fetch fresh from database for security)

---

### 3. get_user_wallet_by_address

**Signature**:
```python
def get_user_wallet_by_address(self, wallet_address: str) -> Optional[UserWallet]:
    """
    Retrieve user wallet by Ethereum address (reverse lookup).

    Args:
        wallet_address: Ethereum wallet address to look up.

    Returns:
        UserWallet if found, None if address not registered.

    Raises:
        DatabaseError: If database query fails.

    Preconditions:
        - wallet_address must be provided

    Postconditions:
        - Returns UserWallet if address registered
        - Returns None if address not found
        - No side effects (read-only operation)

    Example:
        >>> service = UserWalletService(database)
        >>> wallet = service.get_user_wallet_by_address(
        ...     "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B"
        ... )
        >>> if wallet:
        ...     print(f"Telegram User ID: {wallet.telegram_user_id}")
    """
```

**Business Rules**:
- Lookup by unique index (fast indexed query)
- Case-sensitive address comparison (checksummed addresses only)

---

### 4. update_user_wallet

**Signature**:
```python
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
        NotFoundError: If telegram_user_id has no wallet.
        DatabaseError: If database update fails.

    Preconditions:
        - telegram_user_id must exist in database
        - wallet_name must be ≤100 characters if provided

    Postconditions:
        - wallet_name updated to new value
        - updated_at timestamp updated to current time
        - Returns fully populated UserWallet instance

    Example:
        >>> service = UserWalletService(database)
        >>> wallet = service.update_user_wallet(
        ...     telegram_user_id=123456789,
        ...     wallet_name="Updated Name"
        ... )
        >>> assert wallet.wallet_name == "Updated Name"
    """
```

**Business Rules**:
- Only wallet_name is updatable (wallet_address and private_key immutable)
- Validates wallet_name length (max 100 chars)
- Auto-updates updated_at timestamp
- Returns updated record for immediate use

---

### 5. delete_user_wallet

**Signature**:
```python
def delete_user_wallet(self, telegram_user_id: int) -> bool:
    """
    Delete user wallet (admin operation, future feature).

    WARNING: Irreversible operation. User loses access to wallet credentials.
    Not exposed to end users in v1.

    Args:
        telegram_user_id: Telegram user ID of wallet to delete.

    Returns:
        True if wallet was deleted, False if wallet didn't exist.

    Raises:
        DatabaseError: If database delete fails.

    Preconditions:
        - Caller has admin privileges (not checked by this method)

    Postconditions:
        - User wallet record removed from database
        - Returns True if deleted, False if already didn't exist

    Example:
        >>> service = UserWalletService(database)
        >>> deleted = service.delete_user_wallet(123456789)
        >>> if deleted:
        ...     print("Wallet deleted")
        ... else:
        ...     print("Wallet didn't exist")
    """
```

**Business Rules**:
- Admin-only operation (not exposed to bot users in v1)
- Soft delete not implemented (hard delete for v1)
- No cascade deletes (Position/Order/Activity not stored locally)

---

### 6. wallet_exists

**Signature**:
```python
def wallet_exists(self, telegram_user_id: int) -> bool:
    """
    Check if user has a wallet registered.

    Args:
        telegram_user_id: Telegram user ID to check.

    Returns:
        True if user has a wallet, False otherwise.

    Raises:
        DatabaseError: If database query fails.

    Preconditions:
        - telegram_user_id must be provided

    Postconditions:
        - Returns boolean result
        - No side effects (read-only operation)

    Example:
        >>> service = UserWalletService(database)
        >>> if not service.wallet_exists(123456789):
        ...     print("Please initialize wallet with /start")
    """
```

**Business Rules**:
- Optimized query (SELECT COUNT or EXISTS clause)
- Used for wallet initialization guard checks

---

## Dependencies

**Required Imports**:
```python
from typing import Optional
from datetime import datetime
import logging

from web3 import Web3
from eth_account import Account

from poly_boost.models.user_wallet import UserWallet
from poly_boost.core.wallet import Wallet
```

**External Services**:
- `peewee.Database`: Database connection
- `web3.Web3`: Ethereum address validation
- `eth_account.Account`: Private key validation and address derivation

---

## Error Handling Strategy

**Logging**:
```python
logger = logging.getLogger(__name__)

# Example log entries:
logger.info("Creating wallet for user", extra={
    "telegram_user_id": telegram_user_id,
    "wallet_address": wallet_address
})

logger.error("Failed to create wallet", extra={
    "telegram_user_id": telegram_user_id,
    "error": str(e)
}, exc_info=True)
```

**Error Propagation**:
- All errors raised to caller (bot handlers decide how to display)
- Private keys NEVER logged (use `private_key=<REDACTED>` in logs)
- Database errors wrapped with context information

---

## Testing Contract

**Unit Tests Required**:
```python
# tests/unit/services/test_user_wallet_service.py

def test_create_user_wallet_success():
    """Create wallet with valid data succeeds."""

def test_create_user_wallet_invalid_address():
    """Create wallet with invalid address raises ValueError."""

def test_create_user_wallet_invalid_private_key():
    """Create wallet with invalid private key raises ValueError."""

def test_create_user_wallet_key_address_mismatch():
    """Create wallet with mismatched key/address raises ValueError."""

def test_create_user_wallet_duplicate_user():
    """Create wallet for existing user raises IntegrityError."""

def test_create_user_wallet_duplicate_address():
    """Create wallet with existing address raises IntegrityError."""

def test_get_user_wallet_found():
    """Get wallet for existing user returns UserWallet."""

def test_get_user_wallet_not_found():
    """Get wallet for non-existent user returns None."""

def test_update_user_wallet_success():
    """Update wallet name succeeds."""

def test_update_user_wallet_not_found():
    """Update non-existent wallet raises NotFoundError."""

def test_delete_user_wallet_success():
    """Delete existing wallet returns True."""

def test_delete_user_wallet_not_found():
    """Delete non-existent wallet returns False."""

def test_wallet_exists_true():
    """Wallet exists check returns True for existing user."""

def test_wallet_exists_false():
    """Wallet exists check returns False for non-existent user."""
```

**Mock Requirements**:
- Mock database connection (use in-memory SQLite)
- Mock web3.Web3.is_checksum_address for validation tests
- Mock eth_account.Account.from_key for private key tests

---

## Performance Contract

**Latency Targets**:
- `create_user_wallet`: <50ms (single INSERT)
- `get_user_wallet`: <10ms (indexed SELECT)
- `wallet_exists`: <5ms (indexed COUNT/EXISTS)
- `update_user_wallet`: <20ms (indexed UPDATE)
- `delete_user_wallet`: <20ms (indexed DELETE)

**Concurrency**:
- Thread-safe via peewee connection pooling
- No in-memory state (stateless service)
- Supports 100+ concurrent users

---

## Security Contract

**Guarantees**:
- ✅ Private keys NEVER logged
- ✅ Private keys NEVER included in error messages
- ✅ All inputs validated before database operations
- ✅ SQL injection prevented via ORM parameterized queries
- ✅ Unique constraints prevent duplicate wallets

**Assumptions**:
- Database access controls enforce security boundary (see data-model.md)
- Caller (bot handlers) deletes private key messages from Telegram
- Environment provides secure database connection (SSL/TLS)

---

## Usage Examples

### Example 1: Wallet Initialization (Generate New)

```python
from poly_boost.services.user_wallet_service import UserWalletService
from eth_account import Account

# Initialize service
service = UserWalletService(database)

# Generate new wallet
account = Account.create()
wallet_address = account.address
private_key = account.key.hex()

# Store in database
try:
    user_wallet = service.create_user_wallet(
        telegram_user_id=123456789,
        wallet_address=wallet_address,
        private_key=private_key,
        wallet_name="My Bot Wallet"
    )
    print(f"✅ Wallet created: {user_wallet.wallet_address}")
except IntegrityError as e:
    print(f"❌ User already has a wallet")
```

### Example 2: Wallet Lookup (Bot Command)

```python
# Check if user has wallet
telegram_user_id = update.effective_user.id

if not service.wallet_exists(telegram_user_id):
    await update.message.reply_text(
        "Please initialize your wallet with /start"
    )
    return

# Get wallet for trading operations
user_wallet = service.get_user_wallet(telegram_user_id)
wallet = user_wallet.to_wallet()  # Convert to Wallet for services

# Use wallet with other services
positions = position_service.get_positions(wallet)
```

### Example 3: Wallet Name Update

```python
# User changes wallet nickname
telegram_user_id = update.effective_user.id
new_name = update.message.text

try:
    user_wallet = service.update_user_wallet(
        telegram_user_id=telegram_user_id,
        wallet_name=new_name
    )
    await update.message.reply_text(
        f"✅ Wallet renamed to: {user_wallet.wallet_name}"
    )
except ValueError as e:
    await update.message.reply_text(f"❌ {str(e)}")
```

---

## Integration Points

**Called By**:
- `poly_boost.bot.handlers.wallet_handler`: Wallet initialization, info display
- `poly_boost.bot.handlers.position_handler`: Get wallet for position queries
- `poly_boost.bot.handlers.order_handler`: Get wallet for order operations
- `poly_boost.bot.handlers.activity_handler`: Get wallet for activity history
- `poly_boost.bot.conversations.wallet_init`: Wallet initialization conversation

**Calls**:
- `poly_boost.models.user_wallet.UserWallet`: Database model operations
- `poly_boost.core.wallet.Wallet`: Wallet object construction
- `web3.Web3`: Address validation
- `eth_account.Account`: Private key validation

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-05 | Initial contract definition |
