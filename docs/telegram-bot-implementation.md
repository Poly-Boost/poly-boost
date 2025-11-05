# Telegram Bot Implementation

## Overview

This implementation provides complete Telegram Bot functionality for Polymarket wallet management and trading, following the design documents and contract specifications.

## Components Implemented

### 1. Wallet Initialization Conversation (`poly_boost/bot/conversations/wallet_init.py`)

Multi-step conversation handler for wallet setup:
- **States**: WALLET_CHOICE, INPUT_PRIVATE_KEY
- **Entry point**: `/start` command
- **Features**:
  - Generate new EOA wallet using `eth_account.Account.create()`
  - Import existing wallet with private key validation
  - Automatic deletion of private key messages (FR-004)
  - Store wallet credentials in database using UserWalletService

### 2. Wallet Handler (`poly_boost/bot/handlers/wallet_handler.py`)

Wallet management commands:
- **`/wallet`**: Display detailed wallet info (address, balance, portfolio value, position count)
- **`/fund`**: Display funding instructions with QR code for USDC deposits
- **`/profile`**: Link to Polymarket public profile

### 3. Position Handler (`poly_boost/bot/handlers/position_handler.py`)

Position management with pagination and actions:
- **`/positions`**: Display paginated positions list (10 per page)
- **Position selection**: Show detailed view with action buttons
- **Redeem button**: Only shown for redeemable positions (FR-008)
- **Pagination**: Navigation with Previous/Next buttons
- **Empty list handling**: Hides pagination controls (FR-007)
- **Actions**: Market sell, limit sell, redeem winnings

### 4. Order Handler (`poly_boost/bot/handlers/order_handler.py`)

Order management with pagination:
- **`/orders`**: Display paginated active orders list
- **Order selection**: Show detailed view with cancel button
- **Order cancellation**: Cancel orders via OrderService
- **Empty list handling**: No pagination for empty lists (FR-007)

### 5. Activity Handler (`poly_boost/bot/handlers/activity_handler.py`)

Activity history with pagination:
- **`/activities`**: Display paginated activity history (100 most recent)
- **Activity types**: TRADE, SPLIT, MERGE, REDEEM, REWARD, CONVERSION
- **Pagination**: Navigate through activity pages
- **Formatted display**: Type emojis, timestamps, market names, transaction details

### 6. Bot Main (`poly_boost/bot/main.py`)

Application entry point with:
- **Database initialization**: PostgreSQL or SQLite fallback
- **Service initialization**: UserWalletService, PositionService, ActivityService, WalletService
- **Handler registration**: All commands and callback handlers
- **Callback routing**: Centralized routing based on callback_data prefix

### 7. Database Initialization (`poly_boost/scripts/init_db.py`)

Script to create database tables:
- Creates UserWallet table
- Creates core tables (Trade, WalletCheckpoint)
- Supports both PostgreSQL and SQLite

## Architecture

### Service-First Architecture

All handlers are thin wrappers that:
1. Parse input from Telegram updates
2. Call service layer methods (UserWalletService, PositionService, OrderService, ActivityService)
3. Format responses for Telegram (messages, keyboards)
4. Handle Telegram-specific errors

**NO BUSINESS LOGIC IN HANDLERS** - All business logic resides in services layer.

### Database Schema

**user_wallets table**:
```sql
CREATE TABLE user_wallets (
    telegram_user_id BIGINT PRIMARY KEY,
    wallet_address VARCHAR(42) UNIQUE NOT NULL,
    private_key VARCHAR(66) NOT NULL,
    wallet_name VARCHAR(100),
    signature_type INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Error Handling

- **Network errors**: Display user-friendly message and clear stale data (FR-017)
- **Service errors**: Logged with context, user sees generic error
- **Validation errors**: Specific error messages for user input

## Usage

### Setup

1. **Initialize database**:
```bash
python -m poly_boost.scripts.init_db
```

2. **Set environment variables**:
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export DATABASE_URL="postgresql://user:pass@host:port/db"  # Optional, uses SQLite if not set
```

3. **Run bot**:
```bash
python -m poly_boost.bot.main
```

### User Flow

1. **First-time user**:
   - Send `/start`
   - Choose "Generate New Wallet" or "Import Existing Wallet"
   - Wallet credentials stored in database

2. **Existing user**:
   - Send `/start` to see wallet summary
   - Use `/wallet` for detailed info
   - Use `/fund` to get deposit address
   - Use `/positions` to manage positions
   - Use `/orders` to manage orders
   - Use `/activities` to view history

## Key Features

### Security (FR-004)
- Private key messages deleted immediately after processing
- Private keys stored in database (plaintext per FR-019 with access controls)

### Pagination (FR-007)
- 10 items per page for positions, orders, activities
- Pagination controls hidden for empty lists or single page
- Previous/Next buttons with page indicator

### Redeemability (FR-008)
- Redeem button only shown for finalized markets
- Check market status and winning outcome
- Claim rewards through OrderService

### Error Handling (FR-017)
- Network errors display user-friendly messages
- Stale data cleared on errors
- Comprehensive logging for debugging

## File Structure

```
poly_boost/
├── bot/
│   ├── main.py                          # Application entry point
│   ├── conversations/
│   │   ├── __init__.py
│   │   └── wallet_init.py              # Wallet initialization flow
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── wallet_handler.py           # Wallet commands
│   │   ├── position_handler.py         # Position management
│   │   ├── order_handler.py            # Order management
│   │   └── activity_handler.py         # Activity history
│   └── utils/
│       ├── __init__.py
│       └── pagination.py               # Pagination helper (already implemented)
├── models/
│   ├── __init__.py
│   └── user_wallet.py                  # UserWallet model (already implemented)
├── services/
│   ├── __init__.py
│   └── user_wallet_service.py          # UserWallet CRUD (already implemented)
└── scripts/
    ├── __init__.py
    └── init_db.py                      # Database initialization
```

## Dependencies

All handlers use:
- **polymarket_apis SDK** for data and trading operations
- **UserWalletService** for wallet CRUD
- **PaginationHelper** for list pagination
- **ClientFactory** for creating wallet-specific clients

## Testing

To test the implementation:

1. Start the bot
2. Send `/start` to initialize wallet
3. Test each command: `/wallet`, `/fund`, `/profile`, `/positions`, `/orders`, `/activities`
4. Test pagination with multiple pages
5. Test position redeem and order cancel actions
6. Verify error handling by simulating network failures

## Notes

- All handlers follow the contract specifications in `specs/001-telegram-wallet-features/contracts/bot_handlers.md`
- Design follows the architecture in `docs/design/cn/telegram-bot-wallet-feature-design.md`
- Services layer handles all business logic
- Handlers are thin wrappers for Telegram-specific formatting
