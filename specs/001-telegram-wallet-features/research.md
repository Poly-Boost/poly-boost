# Phase 0: Research and Technical Decisions

**Feature**: Telegram Bot Wallet Management & Trading
**Date**: 2025-11-05
**Status**: Complete

## Overview

This document consolidates research findings and technical decisions for implementing wallet management and trading features in the Telegram bot interface. All technology choices align with the existing project architecture and constitution principles.

## Research Tasks Completed

### 1. Telegram Bot Framework Selection

**Decision**: Use `python-telegram-bot` (>=22.5) with async/await pattern

**Rationale**:
- Already listed in project dependencies (pyproject.toml line 16)
- Industry-standard Python library for Telegram bots with 24k+ GitHub stars
- Native async/await support for high concurrency (critical for 100+ users)
- Built-in `ConversationHandler` for multi-step flows (wallet initialization)
- Comprehensive documentation and active community support
- Type hints support for better IDE integration and type safety

**Alternatives Considered**:
- `aiogram`: More modern but would require dependency change and team learning curve
- `python-telegram-bot` v13 (sync): Older version, lacks async performance benefits

**References**:
- Official docs: https://docs.python-telegram-bot.org/
- ConversationHandler guide: https://github.com/python-telegram-bot/python-telegram-bot/wiki/ConversationHandler

---

### 2. Database ORM and Schema Design

**Decision**: Use `peewee` ORM (>=3.17.0) with PostgreSQL (production) / SQLite (development)

**Rationale**:
- Already in project dependencies (pyproject.toml line 8)
- Lightweight ORM suitable for simple CRUD operations (UserWallet table)
- Supports both PostgreSQL (production) and SQLite (development/testing)
- Simple declarative model syntax aligns with Python 3.13 type hints
- No migration tool needed for v1 (single table, no complex relationships)

**Schema Design**:
```python
class UserWallet(peewee.Model):
    telegram_user_id = peewee.BigIntegerField(primary_key=True)  # Telegram user IDs are 64-bit
    wallet_address = peewee.CharField(max_length=42)  # Ethereum address (0x + 40 chars)
    private_key = peewee.CharField(max_length=66)  # 0x + 64 hex chars (plaintext per FR-019)
    wallet_name = peewee.CharField(max_length=100, null=True)  # Optional nickname
    signature_type = peewee.IntegerField(default=0)  # For future EOA/AA support
    created_at = peewee.DateTimeField(default=datetime.now)
    updated_at = peewee.DateTimeField(default=datetime.now)
```

**Alternatives Considered**:
- SQLAlchemy: Overcomplicated for single-table CRUD operations
- Direct SQL: Error-prone, no type safety, harder to test

**Migration Strategy**:
- v1: Manual table creation via peewee.Model.create_table()
- Future: Add Alembic if complex migrations needed

**References**:
- Peewee docs: http://docs.peewee-orm.com/en/latest/
- PostgreSQL best practices: https://wiki.postgresql.org/wiki/Don't_Do_This

---

### 3. Private Key Security Approach

**Decision**: Store private keys in **plaintext** with strict database access controls (FR-019 requirement)

**Rationale**:
- User requirement explicitly states "plaintext storage with strict database access controls"
- Encryption adds complexity and key management overhead for v1
- Security boundary is database access control layer:
  - File-system permissions (database file/socket readable only by bot process user)
  - Network isolation (database not exposed to internet)
  - Authentication (strong database password, SSL connections for PostgreSQL)
  - Audit logging (track all database access)

**Security Measures**:
1. **Application Layer**:
   - Delete private key messages from Telegram immediately after processing (FR-004)
   - Never log private keys or include in error messages
   - Validate private key format before storage (0x prefix, 66 chars, valid hex)
   - Use environment variables for database credentials

2. **Database Layer**:
   - Restrict database user permissions (no GRANT, no DROP)
   - Enable audit logging for all SELECT on user_wallets table
   - Regular backups stored encrypted at rest
   - Row-level security (if PostgreSQL): users can only access their own wallet

3. **Infrastructure Layer**:
   - Database server on private network (no public IP)
   - Firewall rules: only bot server can connect
   - Encrypted connections (SSL/TLS for PostgreSQL)
   - Least privilege: bot process runs as non-root user

**Future Enhancement** (out of scope for v1):
- Encrypt private keys with AES-256-GCM
- Store encryption key in HSM or cloud key management service (AWS KMS, Azure Key Vault)
- Implement key rotation policy

**References**:
- OWASP Key Management: https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html
- PostgreSQL security best practices: https://www.postgresql.org/docs/current/security.html

---

### 4. Pagination Pattern for Lists

**Decision**: Page-based pagination with inline keyboard navigation (10 items per page)

**Rationale**:
- Telegram messages have 4096 character limit; 10 items per page prevents overflow
- Inline keyboards provide intuitive ⬅️/➡️ navigation without typing commands
- Page-based pagination is simpler than cursor-based for small datasets (<1000 items)
- Stateless pagination: page number in callback_data (no server-side session storage)

**Implementation Pattern**:
```python
# Callback data format: "{prefix}_{page_number}"
# Example: "pos_page_2" = positions list page 2

# Keyboard layout:
# [⬅️ Previous] [Page 2/5] [Next ➡️]

# PaginationHelper utility:
class PaginationHelper:
    @staticmethod
    def paginate(items: List[T], page: int = 1, page_size: int = 10) -> PaginatedData[T]:
        # Calculate slice, handle edge cases

    @staticmethod
    def create_pagination_keyboard(
        paginated_data: PaginatedData,
        callback_prefix: str
    ) -> InlineKeyboardMarkup:
        # Generate ⬅️/➡️ buttons with page info
```

**Edge Cases Handled**:
- Empty lists: Hide pagination controls, show "No items" message (FR-007)
- Single page: Hide pagination controls (no nav buttons needed)
- Out of bounds page: Clamp to valid range (1 to total_pages)

**Alternatives Considered**:
- Cursor-based pagination: Overcomplicated for small datasets
- Load more button: Poor UX for navigating backward
- Infinite scroll: Not applicable to Telegram interface

**References**:
- Telegram Bot API InlineKeyboardButton: https://core.telegram.org/bots/api#inlinekeyboardbutton
- UX best practices: https://uxplanet.org/best-practices-for-pagination-88ba1c3a0f45

---

### 5. ConversationHandler Pattern for Wallet Initialization

**Decision**: Use `telegram.ext.ConversationHandler` with state machine pattern

**Rationale**:
- Built-in state management for multi-step user flows
- Timeout support for abandoned conversations (cleanup after 5 minutes)
- Per-user conversation state (multiple users can initialize simultaneously)
- Fallback handlers for /cancel command and error recovery

**State Machine Design**:
```
START state (entry point):
  - Check if wallet already exists
  - If yes: Display wallet info, END
  - If no: Show buttons [Generate New] [Import Existing]

WALLET_CHOICE state:
  - User clicks "Generate New":
    - Generate EOA wallet (eth_account.Account.create())
    - Save to database
    - Display address and private key (with warning)
    - END
  - User clicks "Import Existing":
    - Ask for private key input
    - Go to INPUT_PRIVATE_KEY state

INPUT_PRIVATE_KEY state:
  - User sends message with private key:
    - Validate format (0x prefix, 66 chars, valid hex)
    - If invalid: Show error, stay in INPUT_PRIVATE_KEY
    - If valid: Save to database, delete message, display address, END
  - User sends /cancel: Cancel conversation, END
```

**Timeout Strategy**:
- Conversation timeout: 5 minutes (prevents hanging states)
- After timeout: Clear conversation state, notify user "Session expired"

**Error Handling**:
- Invalid private key format: Re-prompt with helpful error message
- Database save failure: Show generic error, log details, END conversation
- Network errors: Retry 3 times with exponential backoff

**References**:
- ConversationHandler examples: https://github.com/python-telegram-bot/python-telegram-bot/tree/master/examples
- State machine best practices: https://refactoring.guru/design-patterns/state

---

### 6. Position Redeem Button Visibility Logic

**Decision**: Check market finalized status and winning outcome to determine button visibility

**Rationale**:
- FR-008 requires redeem button only when: market ended + outcome won + finalized
- Prevents user frustration (clicking redeem when market not finalized fails)
- Polymarket API provides market status and outcome data

**Implementation**:
```python
def is_position_redeemable(position: Position) -> bool:
    """
    Check if position can be redeemed.

    Returns True only if ALL conditions met:
    1. Market has ended (closed = True)
    2. Market has been finalized (outcome determined)
    3. User holds winning outcome
    """
    market = get_market_info(position.condition_id)

    if not market.closed:
        return False  # Market still active

    if market.outcome is None:
        return False  # Market ended but not finalized

    # Check if user's outcome matches winning outcome
    # (For binary markets: outcome "Yes" or "No")
    return position.outcome == market.winning_outcome
```

**Button Display Logic**:
```python
if is_position_redeemable(position):
    buttons = [[InlineKeyboardButton("🎁 Redeem", callback_data=f"redeem_{position.id}")]]
else:
    buttons = [
        [InlineKeyboardButton("💰 Market Sell", callback_data=f"sell_market_{position.id}")],
        [InlineKeyboardButton("📈 Limit Sell", callback_data=f"sell_limit_{position.id}")]
    ]
```

**Edge Cases**:
- Market finalized but user lost: Show sell buttons (can still sell at current price)
- Market ended but not finalized: Show sell buttons only
- Market ended with tie/invalid outcome: Hide redeem, show sell buttons

**References**:
- Polymarket market lifecycle: https://docs.polymarket.com/#market-lifecycle
- Conditional tokens standard: https://github.com/gnosis/conditional-tokens-contracts

---

### 7. Error Handling for Network Failures

**Decision**: Clear previous data and show error-only message per FR-017

**Rationale**:
- Stale data misleads users (e.g., old positions shown when fetch fails)
- Clear error message helps users understand what went wrong
- Retry suggestion empowers users to resolve transient issues

**Error Message Format**:
```
❌ Error: Unable to load positions

Network request failed. Please try again in a moment.

If the problem persists, check:
- Your internet connection
- Polymarket API status

Use /positions to retry.
```

**Implementation**:
```python
async def handle_positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        positions = await position_service.get_positions(wallet)
        # Display positions...
    except NetworkError as e:
        logger.error(f"Network error loading positions: {e}", extra={
            "telegram_user_id": update.effective_user.id,
            "wallet_address": wallet.address
        })
        await update.message.reply_text(
            "❌ Error: Unable to load positions\n\n"
            "Network request failed. Please try again in a moment.\n\n"
            "Use /positions to retry."
        )
        # DO NOT show old data from context.user_data
        context.user_data.pop('positions', None)  # Clear stale data
```

**Error Categories**:
1. **Network errors**: Timeout, connection refused, DNS failure
2. **API errors**: 4xx/5xx responses from Polymarket API
3. **Validation errors**: Invalid response format, missing required fields
4. **Database errors**: Connection lost, constraint violations

**References**:
- Error message UX best practices: https://uxdesign.cc/how-to-write-good-error-messages-858e4551cd4
- Retry strategies: https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/

---

## Technology Stack Summary

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Bot Framework | python-telegram-bot | >=22.5 | Async support, ConversationHandler, type hints |
| ORM | peewee | >=3.17.0 | Lightweight, PostgreSQL/SQLite support |
| Database | PostgreSQL / SQLite | 15+ / 3.x | Production/dev parity, peewee compatible |
| Wallet Library | eth_account (web3.py) | >=7.0.0 | Standard Ethereum wallet generation |
| Blockchain Client | polymarket-apis, py-clob-client | >=0.3.5, >=0.25.0 | Official Polymarket integration |
| Type Checking | Python type hints | 3.13 native | IDE support, type safety |
| Testing | pytest, pytest-asyncio | Latest | Async test support, mocking |

## Best Practices Applied

### 1. Service-First Architecture
- All business logic in `UserWalletService` (CRUD), existing services (positions, orders)
- Bot handlers are thin wrappers (parse input → call service → format output)
- Services are interface-agnostic (reusable by CLI, API)

### 2. Security-First Design
- Private keys never logged or displayed after deletion
- Input validation (wallet addresses, private key format)
- Environment variables for secrets (bot token, database credentials)
- Strict database access controls (file permissions, network isolation)

### 3. Error Handling and Observability
- Structured logging with context (telegram_user_id, wallet_address, operation)
- Clear user-facing error messages without internal details
- Retry logic for transient failures (network, database)

### 4. Type Safety
- All functions use Python type hints
- peewee models define field types
- Generic pagination helper (`PaginatedData[T]`)

### 5. Testing Strategy
- Unit tests: Services and utilities (mock database, external APIs)
- Integration tests: ConversationHandler flow (mock Telegram)
- Contract tests: Handler interfaces (ensure correct service calls)

## Open Questions Resolved

1. **Q: How to handle concurrent redemption attempts on same position?**
   **A**: Blockchain-level prevention (nonce-based transaction ordering). Bot layer shows optimistic UI, blockchain rejects duplicate transaction.

2. **Q: How to handle position/order modified externally?**
   **A**: Always fetch fresh data from API on command invocation. No local caching of positions/orders in bot context.

3. **Q: How to handle lost Telegram account access?**
   **A**: Out of scope for v1. Future: Add recovery mechanism (email verification, secondary auth).

4. **Q: How to handle expired/invalid wallet sessions?**
   **A**: Wallets stored in database don't expire. Each bot command fetches wallet from database. No session management needed.

## Implementation Readiness

✅ All technical decisions finalized
✅ No external dependencies requiring procurement
✅ All libraries already in project dependencies
✅ Database schema designed
✅ Error handling patterns defined
✅ Security measures documented
✅ Testing strategy defined

**Ready to proceed to Phase 1: Design & Contracts**
