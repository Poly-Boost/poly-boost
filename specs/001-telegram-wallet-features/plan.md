# Implementation Plan: Telegram Bot Wallet Management & Trading

**Branch**: `001-telegram-wallet-features` | **Date**: 2025-11-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-telegram-wallet-features/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement comprehensive wallet management and trading features for the Telegram bot interface, enabling users to initialize/import wallets, view positions with pagination, manage orders, and view activity history. The implementation follows the Service-First Architecture principle, with all business logic in the services layer and the bot providing a thin interface layer. This feature extends the existing position_service.py, order_service.py, and activity_service.py with a new user_wallet_service.py for user-wallet associations, plus bot handlers for /start, /wallet, /positions, /orders, /activities, and /fund commands.

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: python-telegram-bot (>=22.5), polymarket-apis (>=0.3.5), py-clob-client (>=0.25.0), web3 (>=7.0.0), peewee (>=3.17.0), FastAPI (>=0.119.0)
**Storage**: PostgreSQL (production) / SQLite (development) via peewee ORM for user wallet data
**Testing**: pytest with mocks for external APIs (Polymarket API, Polygon RPC, Telegram API)
**Target Platform**: Linux server (containerized deployment typical for bots)
**Project Type**: Single (multi-interface: CLI, REST API, Telegram Bot sharing services layer)
**Performance Goals**:
- Bot command response <3s for data queries (positions, orders, activities)
- Pagination rendering <1s per page
- Wallet initialization <1min end-to-end including user interaction
- Transaction operations <5s excluding blockchain confirmation time

**Constraints**:
- Private keys stored in plaintext with strict database access controls (no encryption in v1)
- Pagination fixed at 10 items per page to prevent Telegram message size limits
- Redeem button visibility requires market finalized state check
- Empty lists hide pagination controls
- Network errors clear previous data and show error only

**Scale/Scope**:
- Support 100+ concurrent users initially
- Handle wallets with 100+ positions efficiently
- Database schema supports indefinite user wallet retention
- ~1500 LOC for new services + handlers + utilities
- 8 new modules: 1 service, 4 handlers, 1 conversation, 1 utility, 1 database model

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Service-First Architecture (NON-NEGOTIABLE) ✅

**Status**: PASS
**Rationale**: Feature design explicitly places all business logic in services layer:
- New `UserWalletService` in `poly_boost/services/user_wallet_service.py` for wallet CRUD
- Extends existing `PositionService`, `OrderService`, `ActivityService` for data queries
- Bot handlers in `poly_boost/bot/handlers/` are thin wrappers that only call services and format responses
- `PaginationHelper` utility provides reusable pagination logic without business logic

**Verification**:
- [ ] All business logic resides in `poly_boost/services/`
- [ ] Bot handlers only handle: parameter parsing, service calls, response formatting, Telegram-specific error handling
- [ ] No duplication of wallet/position/order logic across interfaces

### Multi-Interface Consistency ✅

**Status**: PASS
**Rationale**: While this feature focuses on Telegram Bot interface, the underlying services (`UserWalletService`, existing `PositionService`, `OrderService`, `ActivityService`) are interface-agnostic and can be consumed by CLI and REST API in the future.

**Future Work**: After bot implementation, expose equivalent functionality in:
- CLI: `poly-boost wallet init`, `poly-boost positions list`, etc.
- REST API: `/api/v1/user-wallets`, `/api/v1/positions`, etc.

### Security-First Design (NON-NEGOTIABLE) ✅

**Status**: PASS (with documented v1 limitation)
**Rationale**:
- Private keys stored in database plaintext per FR-019 with strict access controls (file-system permissions, network isolation, authentication)
- Private key messages deleted immediately after processing (FR-004)
- No private keys in logs or error messages
- Environment variables for bot token (`.env` file)
- Input validation for wallet addresses (checksum validation via web3.py)
- Private key validation during import (eth_account.Account.from_key)

**Known Limitation**: No encryption at rest in v1. Database access controls are the security boundary. Encryption planned for future iterations per design doc.

**Verification**:
- [ ] Private keys never logged or exposed in Telegram messages after deletion
- [ ] Database credentials in `.env`, not hardcoded
- [ ] Wallet address checksum validation before storage
- [ ] Private key format validation (0x prefix, 66 chars) before storage

### Polymarket Client Integration ✅

**Status**: PASS
**Rationale**:
- All blockchain interactions use official `polymarket_apis` and `py-clob-client`
- Services (`WalletService`, `OrderService`, `PositionService`) already integrate `ClobClient`
- New `UserWalletService` converts stored wallet to `Wallet` object for client usage

**Verification**:
- [ ] No direct web3 contract calls for Polymarket operations
- [ ] All trading/position/order operations use `ClobClient` or `polymarket_apis`

### Configuration Management ✅

**Status**: PASS
**Rationale**:
- Bot token in `config/config.yaml` or `.env` (loaded via `python-dotenv`)
- Database connection config in `config/config.yaml`
- Pagination page_size configurable (default 10)
- Existing `config_loader.py` pattern extended for bot config

**Verification**:
- [ ] Bot token loaded from environment variable
- [ ] Database connection string loaded from config
- [ ] No hardcoded configuration in code

### Robust Error Handling and Observability ✅

**Status**: PASS
**Rationale**:
- Services layer logs all operations (wallet creation, position queries, order cancellations)
- Bot handlers catch exceptions and display user-friendly error messages
- Network errors clear previous data per FR-017
- Structured logging with context (telegram_user_id, wallet_address, operation type)
- Retry logic for blockchain operations (existing in services)

**Verification**:
- [ ] All service methods have try-catch with logging
- [ ] Bot handlers display clear error messages without exposing internal details
- [ ] Log entries include telegram_user_id and operation context

### Test Coverage for Critical Paths ✅

**Status**: PASS
**Rationale**: Tests required for:
- `UserWalletService`: create, get, update, delete, wallet_exists
- Wallet initialization conversation flow
- Position pagination logic (PaginationHelper)
- Redeem button visibility logic (market finalized check)
- Empty list handling (pagination hidden)
- Error handling (network errors, invalid private keys)

**Testing Strategy**:
- `tests/unit/services/test_user_wallet_service.py`: Service CRUD operations with mock database
- `tests/unit/bot/test_pagination_helper.py`: Pagination edge cases
- `tests/integration/bot/test_wallet_init_conversation.py`: Full conversation flow with mock Telegram
- `tests/contract/bot/test_position_handler.py`: Handler contracts with mock services

**Verification**:
- [ ] 80%+ coverage for `UserWalletService`
- [ ] Edge cases tested: empty lists, invalid inputs, network errors
- [ ] Mock Telegram bot for conversation testing

### Summary

**Overall Status**: ✅ PASS (all gates satisfied)

**No violations requiring justification.** This feature is a straightforward extension of the existing architecture pattern with services layer providing business logic and bot handlers providing interface layer. Security limitation (plaintext storage) is documented and approved per FR-019 with mitigations (access controls).

## Project Structure

### Documentation (this feature)

```text
specs/001-telegram-wallet-features/
├── spec.md              # Feature specification (user stories, requirements)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output - Technical research and decisions
├── data-model.md        # Phase 1 output - Database schema and entities
├── quickstart.md        # Phase 1 output - Developer setup guide
├── contracts/           # Phase 1 output - Service interfaces and bot handlers
│   ├── user_wallet_service.md  # UserWalletService interface contract
│   ├── pagination_helper.md    # PaginationHelper utility contract
│   └── bot_handlers.md         # Bot handler interfaces
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
poly-boost/
├── poly_boost/                    # Main package
│   ├── core/                     # Core logic
│   │   ├── config_loader.py      # [EXISTING] Configuration management
│   │   ├── wallet.py             # [EXISTING] Wallet data class
│   │   └── wallet_manager.py     # [EXISTING] Wallet management
│   │
│   ├── services/                 # Business services layer (Service-First Architecture)
│   │   ├── user_wallet_service.py     # [NEW] User-wallet association CRUD
│   │   ├── wallet_service.py          # [EXISTING] Blockchain wallet operations
│   │   ├── position_service.py        # [EXISTING] Position queries
│   │   ├── order_service.py           # [EXISTING] Order management
│   │   └── activity_service.py        # [EXISTING] Activity history
│   │
│   ├── bot/                      # Telegram bot interface layer (thin wrapper)
│   │   ├── main.py               # [EXISTING] Bot initialization
│   │   ├── keyboards.py          # [EXISTING] Keyboard layouts
│   │   │
│   │   ├── handlers/             # Command and callback handlers
│   │   │   ├── __init__.py
│   │   │   ├── wallet_handler.py      # [NEW] /start, /wallet, /fund, /profile
│   │   │   ├── position_handler.py    # [EXTEND] /positions with pagination
│   │   │   ├── order_handler.py       # [NEW] /orders with cancellation
│   │   │   └── activity_handler.py    # [NEW] /activities with pagination
│   │   │
│   │   ├── conversations/        # Multi-step conversation flows
│   │   │   └── wallet_init.py         # [NEW] Wallet initialization ConversationHandler
│   │   │
│   │   └── utils/                # Bot utilities
│   │       └── pagination.py          # [NEW] PaginationHelper utility
│   │
│   ├── models/                   # Database models (peewee ORM)
│   │   └── user_wallet.py        # [NEW] UserWallet model
│   │
│   ├── api/                      # [EXISTING] FastAPI REST API (future enhancement)
│   └── cli.py                    # [EXISTING] CLI interface (future enhancement)
│
├── tests/                        # Test suite
│   ├── unit/
│   │   ├── services/
│   │   │   └── test_user_wallet_service.py  # [NEW] Service unit tests
│   │   └── bot/
│   │       └── test_pagination_helper.py    # [NEW] Pagination unit tests
│   ├── integration/
│   │   └── bot/
│   │       └── test_wallet_init_conversation.py  # [NEW] Conversation flow tests
│   └── contract/
│       └── bot/
│           ├── test_wallet_handler.py       # [NEW] Handler contract tests
│           ├── test_position_handler.py     # [NEW] Handler contract tests
│           ├── test_order_handler.py        # [NEW] Handler contract tests
│           └── test_activity_handler.py     # [NEW] Handler contract tests
│
├── config/                       # Configuration
│   └── config.yaml               # [EXTEND] Add bot configuration
│
├── docs/                         # Documentation
│   └── design/
│       └── cn/
│           └── telegram-bot-wallet-feature-design.md  # [EXISTING] Design doc
│
├── .env                          # [EXTEND] Add TELEGRAM_BOT_TOKEN, DB credentials
└── pyproject.toml                # [EXISTING] Dependencies already include python-telegram-bot
```

**Structure Decision**: This project uses **Option 1: Single project** structure with multi-interface support (CLI, API, Bot). The architecture follows the Service-First principle where:
1. **Services layer** (`poly_boost/services/`) contains all business logic (existing services extended, new `UserWalletService` added)
2. **Interface layers** (`poly_boost/bot/`, `poly_boost/api/`, `poly_boost/cli.py`) are thin wrappers that call services and format responses
3. **Core layer** (`poly_boost/core/`) provides shared utilities and data structures
4. **Models layer** (`poly_boost/models/`) defines database schema via peewee ORM

This feature focuses on the **bot interface layer** with supporting services and database models. Future work will expose the same functionality through CLI and REST API interfaces.

## Complexity Tracking

**No violations to justify.** This feature adheres to all constitution principles without requiring additional complexity.
