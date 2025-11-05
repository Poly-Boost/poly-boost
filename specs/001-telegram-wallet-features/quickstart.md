# Quickstart Guide: Telegram Bot Wallet Features

**Feature**: Telegram Bot Wallet Management & Trading
**Date**: 2025-11-05
**Target Audience**: Developers implementing this feature

## Overview

This guide walks through setting up the development environment, implementing the feature components, and testing the Telegram bot wallet management functionality.

**Estimated Setup Time**: 30 minutes
**Estimated Implementation Time**: 8-12 hours (following tasks.md)

---

## Prerequisites

### Required Tools

- Python 3.13+ installed
- Git (for version control)
- PostgreSQL 15+ (production) OR SQLite 3.x (development)
- Telegram account (for creating bot token)
- Text editor / IDE (VS Code, PyCharm recommended)

### Required Knowledge

- Python async/await patterns
- Telegram bot development basics
- Ethereum wallet concepts (addresses, private keys)
- SQL database concepts

---

## Step 1: Environment Setup

### 1.1 Clone Repository and Switch Branch

```bash
# Clone repository (if not already cloned)
git clone https://github.com/your-org/poly-boost.git
cd poly-boost

# Switch to feature branch
git checkout 001-telegram-wallet-features

# Verify branch
git branch  # Should show * 001-telegram-wallet-features
```

### 1.2 Create Python Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Verify Python version
python --version  # Should show Python 3.13.x
```

### 1.3 Install Dependencies

```bash
# Install all project dependencies
pip install -e .

# Verify installation
python -c "import telegram; print(telegram.__version__)"  # Should print 22.5+
python -c "import peewee; print(peewee.__version__)"      # Should print 3.17.0+
```

**Dependencies Installed**:
- `python-telegram-bot >= 22.5`: Bot framework
- `peewee >= 3.17.0`: ORM for database
- `web3 >= 7.0.0`: Ethereum utilities
- `eth-account`: Wallet generation
- `polymarket-apis >= 0.3.5`: Polymarket client
- `python-dotenv >= 1.1.1`: Environment variables

---

## Step 2: Database Setup

### 2.1 Create Database (PostgreSQL)

**For Production**:

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database and user
CREATE DATABASE polyboost_bot;
CREATE USER polyboost_bot_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE polyboost_bot TO polyboost_bot_user;

# Exit psql
\q
```

**For Development (SQLite)**:

```bash
# SQLite database will be auto-created on first run
# No manual setup required
```

### 2.2 Configure Database Connection

Create/update `.env` file in project root:

```bash
# .env

# Database (choose one)
# PostgreSQL (production):
DATABASE_URL=postgresql://polyboost_bot_user:your_secure_password@localhost:5432/polyboost_bot

# SQLite (development):
# DATABASE_URL=sqlite:///polyboost_bot.db

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here  # Get from @BotFather

# Polymarket (existing)
POLYMARKET_API_KEY=your_api_key
POLYGON_RPC_URL=https://polygon-rpc.com
```

**Security Note**: Never commit `.env` file to version control! It should be in `.gitignore`.

### 2.3 Initialize Database Schema

```bash
# Run database migration
python -m poly_boost.models.user_wallet create_table

# Verify table created
# PostgreSQL:
psql -U polyboost_bot_user -d polyboost_bot -c "\d user_wallets"

# SQLite:
sqlite3 polyboost_bot.db ".schema user_wallets"
```

**Expected Output**:
```
Table "public.user_wallets"
     Column        |  Type   | Modifiers
-------------------+---------+-----------
 telegram_user_id  | bigint  | not null
 wallet_address    | varchar | not null
 private_key       | varchar | not null
 wallet_name       | varchar |
 signature_type    | integer | default 0
 created_at        | timestamp | default now()
 updated_at        | timestamp | default now()
Indexes:
    "user_wallets_pkey" PRIMARY KEY, btree (telegram_user_id)
    "user_wallets_wallet_address_key" UNIQUE, btree (wallet_address)
```

---

## Step 3: Telegram Bot Setup

### 3.1 Create Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow prompts:
   - **Bot name**: "Polymarket Copy Trading Bot" (or your choice)
   - **Bot username**: "polyboost_bot" (must be unique, ends with "bot")
4. Copy the bot token (format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)
5. Add token to `.env` file as `TELEGRAM_BOT_TOKEN`

### 3.2 Configure Bot Settings

Send these commands to @BotFather:

```
/setcommands
Select your bot: @polyboost_bot
Paste command list:

start - Initialize wallet or view wallet info
wallet - View detailed wallet information
fund - Get deposit address and instructions
profile - View Polymarket public profile
positions - View and manage market positions
orders - View and cancel active orders
activities - View transaction history
```

---

## Step 4: Project Structure Verification

Verify the following directories exist:

```bash
# Check project structure
tree poly_boost -L 2

# Expected output:
poly_boost/
├── core/
│   ├── config_loader.py
│   ├── wallet.py
│   └── wallet_manager.py
├── services/
│   ├── wallet_service.py
│   ├── position_service.py
│   ├── order_service.py
│   ├── activity_service.py
│   └── user_wallet_service.py  # [NEW - to be created]
├── bot/
│   ├── main.py
│   ├── handlers/
│   │   ├── wallet_handler.py  # [NEW - to be created]
│   │   ├── position_handler.py  # [EXTEND existing]
│   │   ├── order_handler.py  # [NEW - to be created]
│   │   └── activity_handler.py  # [NEW - to be created]
│   ├── conversations/
│   │   └── wallet_init.py  # [NEW - to be created]
│   └── utils/
│       └── pagination.py  # [NEW - to be created]
├── models/
│   └── user_wallet.py  # [NEW - to be created]
└── ...
```

---

## Step 5: Implementation Checklist

Follow this order to implement the feature (detailed in `tasks.md`):

### Phase 1: Core Services and Models

- [ ] **Task 1**: Implement `poly_boost/models/user_wallet.py` (UserWallet database model)
- [ ] **Task 2**: Implement `poly_boost/services/user_wallet_service.py` (CRUD service)
- [ ] **Task 3**: Implement `poly_boost/bot/utils/pagination.py` (PaginationHelper utility)
- [ ] **Task 4**: Write unit tests for UserWalletService and PaginationHelper

### Phase 2: Bot Handlers

- [ ] **Task 5**: Implement `poly_boost/bot/conversations/wallet_init.py` (Wallet initialization conversation)
- [ ] **Task 6**: Implement `poly_boost/bot/handlers/wallet_handler.py` (/start, /wallet, /fund, /profile)
- [ ] **Task 7**: Extend `poly_boost/bot/handlers/position_handler.py` (Add pagination, redeem)
- [ ] **Task 8**: Implement `poly_boost/bot/handlers/order_handler.py` (/orders, cancellation)
- [ ] **Task 9**: Implement `poly_boost/bot/handlers/activity_handler.py` (/activities)
- [ ] **Task 10**: Register handlers in `poly_boost/bot/main.py`

### Phase 3: Testing and Integration

- [ ] **Task 11**: Write integration tests for conversation flows
- [ ] **Task 12**: Write contract tests for handlers
- [ ] **Task 13**: Manual testing with real Telegram bot
- [ ] **Task 14**: Update configuration files and documentation

---

## Step 6: Running the Bot (Development)

### 6.1 Start Bot in Development Mode

```bash
# Ensure virtual environment activated
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows

# Run bot
python -m poly_boost.bot.main

# Expected output:
# INFO - Starting Polymarket Copy Trading Bot...
# INFO - Bot username: @polyboost_bot
# INFO - Listening for messages...
```

### 6.2 Test Basic Commands

1. Open Telegram and search for your bot (e.g., `@polyboost_bot`)
2. Send `/start` command
3. Expected response:
   ```
   Welcome to Polymarket Bot! 🎉

   Please set up your wallet to get started:

   [🆕 Generate New Wallet] [📥 Import Existing Wallet]
   ```
4. Click "Generate New Wallet"
5. Expected response:
   ```
   ✅ Wallet Created

   Address: `0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B`

   ⚠️ SAVE YOUR PRIVATE KEY:
   `0x1234...5678...abcd`

   Keep this key safe! If lost, you cannot recover your wallet.
   ```
6. Send `/wallet` command to verify wallet stored

---

## Step 7: Testing with Mock Data

### 7.1 Create Test Wallet

```python
# Run in Python REPL or test script
from eth_account import Account

# Generate test wallet
account = Account.create()
print(f"Address: {account.address}")
print(f"Private Key: {account.key.hex()}")

# Use this wallet for testing import flow
```

### 7.2 Fund Test Wallet (Polygon Testnet)

**Option 1: Use Polygon Mumbai Faucet** (if testing on testnet):
1. Visit https://faucet.polygon.technology/
2. Paste test wallet address
3. Request MATIC and test USDC

**Option 2: Use Mainnet with Small Amounts** (if testing on mainnet):
1. Transfer 0.1 MATIC (for gas) to test wallet
2. Transfer 1 USDC to test wallet
3. Use wallet for real testing

---

## Step 8: Development Workflow

### 8.1 Code → Test → Commit Cycle

```bash
# 1. Write code (e.g., implement UserWalletService)

# 2. Run unit tests
pytest tests/unit/services/test_user_wallet_service.py -v

# 3. Run integration tests
pytest tests/integration/bot/test_wallet_init_conversation.py -v

# 4. Manual test with bot
python -m poly_boost.bot.main
# (Test commands in Telegram)

# 5. Commit changes
git add poly_boost/services/user_wallet_service.py
git commit -m "feat: implement UserWalletService"
```

### 8.2 Debugging Tips

**Enable Debug Logging**:
```python
# In poly_boost/bot/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Test Services Independently**:
```python
# Test service without bot
from poly_boost.services.user_wallet_service import UserWalletService

service = UserWalletService(database)
wallet = service.create_user_wallet(
    telegram_user_id=123456789,
    wallet_address="0x...",
    private_key="0x..."
)
print(wallet)
```

**Mock External APIs**:
```python
# In tests, mock Polymarket API
from unittest.mock import Mock, patch

@patch('poly_boost.services.position_service.ClobClient')
def test_get_positions(mock_clob):
    mock_clob.return_value.get_positions.return_value = [...]
    # Test your code
```

---

## Step 9: Common Issues and Solutions

### Issue 1: "ModuleNotFoundError: No module named 'telegram'"

**Solution**:
```bash
pip install python-telegram-bot
# Verify installation:
python -c "import telegram; print('OK')"
```

### Issue 2: "peewee.OperationalError: unable to open database file"

**Solution**:
```bash
# Check DATABASE_URL in .env
# For SQLite, ensure directory exists:
mkdir -p $(dirname "polyboost_bot.db")

# For PostgreSQL, verify connection:
psql -U polyboost_bot_user -d polyboost_bot -c "SELECT 1"
```

### Issue 3: "telegram.error.InvalidToken: Invalid token"

**Solution**:
```bash
# Check TELEGRAM_BOT_TOKEN in .env
# Verify token format: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
# Get new token from @BotFather if needed
```

### Issue 4: "Private key validation failed"

**Solution**:
```python
# Ensure private key has 0x prefix and 64 hex characters
# Valid: 0x1234567890abcdef...
# Invalid: 1234567890abcdef... (missing 0x)
# Invalid: 0x123 (too short)
```

### Issue 5: Bot not responding to commands

**Solution**:
```bash
# 1. Check bot is running (no errors in terminal)
# 2. Verify bot username is correct in Telegram
# 3. Send /start to initialize conversation
# 4. Check logs for errors:
tail -f logs/bot.log
```

---

## Step 10: Pre-Commit Checklist

Before committing code, verify:

- [ ] All unit tests pass: `pytest tests/unit/ -v`
- [ ] All integration tests pass: `pytest tests/integration/ -v`
- [ ] Code follows constitution principles (Service-First Architecture)
- [ ] No private keys or secrets hardcoded
- [ ] All functions have type hints
- [ ] All functions have docstrings
- [ ] Manual testing completed with bot
- [ ] No linting errors: `pylint poly_boost/`
- [ ] Git commit message follows convention: `feat: ...`, `fix: ...`, etc.

---

## Step 11: Deployment (Production)

### 11.1 Pre-Deployment Checks

- [ ] Database migrated (PostgreSQL in production)
- [ ] Environment variables set (`.env` for production)
- [ ] Bot token configured (production bot from @BotFather)
- [ ] Logging configured (file logging enabled)
- [ ] Database backups scheduled
- [ ] Monitoring alerts configured

### 11.2 Deploy Bot

**Option 1: systemd service** (Linux):

```bash
# Create service file: /etc/systemd/system/polyboost-bot.service
[Unit]
Description=Polymarket Copy Trading Bot
After=network.target

[Service]
Type=simple
User=polyboost
WorkingDirectory=/opt/polyboost
ExecStart=/opt/polyboost/.venv/bin/python -m poly_boost.bot.main
Restart=always

[Install]
WantedBy=multi-user.target

# Enable and start service
sudo systemctl enable polyboost-bot
sudo systemctl start polyboost-bot

# Check status
sudo systemctl status polyboost-bot
```

**Option 2: Docker** (containerized):

```dockerfile
# Dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY . /app

RUN pip install -e .

CMD ["python", "-m", "poly_boost.bot.main"]
```

```bash
# Build and run
docker build -t polyboost-bot .
docker run -d --name polyboost-bot --env-file .env polyboost-bot

# View logs
docker logs -f polyboost-bot
```

### 11.3 Post-Deployment Verification

```bash
# 1. Verify bot responds to /start
# 2. Check logs for errors
tail -f logs/bot.log

# 3. Monitor database connections
psql -U polyboost_bot_user -d polyboost_bot -c "SELECT COUNT(*) FROM user_wallets;"

# 4. Test all commands manually
# 5. Monitor error rates in logs
```

---

## Step 12: Next Steps

After completing this feature:

1. **Implement Multi-Interface Consistency**:
   - Expose wallet management in CLI: `poly-boost wallet init`
   - Expose wallet management in REST API: `/api/v1/user-wallets`

2. **Enhance Security** (future iteration):
   - Add private key encryption at rest
   - Implement HSM/KMS integration
   - Add 2FA for sensitive operations

3. **Add Advanced Features**:
   - Multi-wallet support per user
   - Wallet recovery mechanism
   - Portfolio analytics
   - Price alerts and notifications

4. **Optimize Performance**:
   - Add caching for frequently accessed data
   - Implement connection pooling
   - Add rate limiting for API calls

---

## Resources

### Documentation

- [python-telegram-bot docs](https://docs.python-telegram-bot.org/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [peewee ORM docs](http://docs.peewee-orm.com/)
- [Polymarket API docs](https://docs.polymarket.com/)
- [eth-account docs](https://eth-account.readthedocs.io/)

### Design Documents

- [Feature Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Research](./research.md)
- [Data Model](./data-model.md)
- [Service Contracts](./contracts/)

### Support

- **Issues**: Report bugs in GitHub Issues
- **Questions**: Ask in project Discord/Slack
- **Code Review**: Tag @team-leads in pull requests

---

## Troubleshooting Contact

For urgent issues:
- **Database Issues**: Contact @db-admin
- **Telegram Bot Issues**: Contact @bot-maintainer
- **Security Concerns**: Contact @security-team

---

**Happy Coding! 🚀**
