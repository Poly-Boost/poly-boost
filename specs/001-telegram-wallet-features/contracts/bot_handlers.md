# Bot Handlers Contract

**Module**: `poly_boost.bot.handlers`
**Purpose**: Telegram bot command and callback handlers (thin interface layer)
**Pattern**: Handler functions calling services and formatting responses

## Architecture Principle

**Service-First Architecture**: All handlers are thin wrappers that:
1. Parse input from Telegram updates
2. Call service layer methods (UserWalletService, PositionService, OrderService, ActivityService)
3. Format responses for Telegram (messages, keyboards)
4. Handle Telegram-specific errors (network errors, user input errors)

**NO BUSINESS LOGIC IN HANDLERS**: All business logic resides in services layer.

---

## WalletHandler

**Module**: `poly_boost.bot.handlers.wallet_handler`
**Commands**: `/start`, `/wallet`, `/fund`, `/profile`

### 1. start_command

**Signature**:
```python
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle /start command - wallet initialization or display wallet info.

    If user has no wallet, starts WalletInitConversation (ConversationHandler entry point).
    If user has wallet, displays wallet address and balance.

    Args:
        update: Telegram update containing command.
        context: Bot context with bot_data (services) and user_data (session).

    Returns:
        ConversationHandler state (WALLET_CHOICE) or ConversationHandler.END.

    Raises:
        None (errors caught and displayed to user).

    Flow:
        1. Get telegram_user_id from update.effective_user.id
        2. Check if wallet exists (user_wallet_service.wallet_exists)
        3. If exists: Display wallet info (address, balance), END
        4. If not exists: Start WalletInitConversation, return WALLET_CHOICE state

    Example Output (existing wallet):
        👛 Your Wallet

        Address: `0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B`
        Balance: $125.50 USDC
        Portfolio Value: $340.20

        Use /wallet for details or /fund to add funds.

    Example Output (no wallet):
        Welcome to Polymarket Bot! 🎉

        Please set up your wallet to get started:

        [🆕 Generate New Wallet] [📥 Import Existing Wallet]
    """
```

**Service Calls**:
- `user_wallet_service.wallet_exists(telegram_user_id)` → bool
- `user_wallet_service.get_user_wallet(telegram_user_id)` → UserWallet
- `wallet_service.get_balance(wallet)` → Decimal
- `position_service.get_position_value(wallet)` → Decimal

**Error Handling**:
| Error Type | Action |
|------------|--------|
| Service unavailable | Display "⚠️ Service temporarily unavailable. Try again later." |
| Network error | Display "❌ Network error. Please check connection and retry." |

---

### 2. wallet_command

**Signature**:
```python
async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /wallet command - display detailed wallet information.

    Shows wallet address, USDC balance, portfolio value, and position count.

    Args:
        update: Telegram update containing command.
        context: Bot context.

    Returns:
        None

    Raises:
        None (errors caught and displayed to user).

    Preconditions:
        - User must have initialized wallet (guard check)

    Example Output:
        💼 Wallet Details

        Address: `0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B`
        Balance: $125.50 USDC
        Portfolio Value: $340.20
        Total Positions: 8

        Use /positions to view positions.
        Use /fund to add funds.
    """
```

**Service Calls**:
- `user_wallet_service.get_user_wallet(telegram_user_id)` → UserWallet | None
- `wallet_service.get_balance(wallet)` → Decimal
- `position_service.get_position_summary(wallet)` → dict

**Guard Check**:
```python
if not user_wallet:
    await update.message.reply_text(
        "Please initialize your wallet with /start first."
    )
    return
```

---

### 3. fund_command

**Signature**:
```python
async def fund_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /fund command - display funding instructions.

    Shows wallet address for deposits with QR code and instructions.

    Args:
        update: Telegram update containing command.
        context: Bot context.

    Returns:
        None

    Example Output:
        💰 Fund Your Wallet

        Send USDC (Polygon network) to:
        `0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B`

        [QR CODE IMAGE]

        ⚠️ Important:
        - Use USDC on Polygon network ONLY
        - Double-check address before sending
        - Funds sent to wrong network may be lost

        Balance updates may take 1-2 minutes.
    """
```

**Service Calls**:
- `user_wallet_service.get_user_wallet(telegram_user_id)` → UserWallet | None

**QR Code Generation**:
```python
import qrcode
from io import BytesIO

# Generate QR code for address
qr = qrcode.make(wallet_address)
buffer = BytesIO()
qr.save(buffer, format='PNG')
buffer.seek(0)

# Send photo
await update.message.reply_photo(
    photo=buffer,
    caption=f"Wallet Address: `{wallet_address}`\n\nScan to copy address."
)
```

---

### 4. profile_command

**Signature**:
```python
async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /profile command - link to Polymarket public profile.

    Args:
        update: Telegram update containing command.
        context: Bot context.

    Returns:
        None

    Example Output:
        📊 Your Polymarket Profile

        View your public profile:
        https://polymarket.com/profile/0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B
    """
```

**Service Calls**:
- `user_wallet_service.get_user_wallet(telegram_user_id)` → UserWallet | None

**Profile URL Format**:
```
https://polymarket.com/profile/{wallet_address}
```

---

## PositionHandler

**Module**: `poly_boost.bot.handlers.position_handler`
**Commands**: `/positions`
**Callbacks**: `pos_page_{page}`, `pos_select_{index}`, `pos_redeem_{token_id}`, `pos_sell_market_{token_id}`, `pos_sell_limit_{token_id}`

### 1. positions_command

**Signature**:
```python
async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /positions command - display paginated positions list.

    Args:
        update: Telegram update containing command.
        context: Bot context.

    Returns:
        None

    Flow:
        1. Get user wallet
        2. Fetch positions from service
        3. Paginate positions (page 1, page_size 10)
        4. Format message with position summaries
        5. Create inline keyboard with pagination and selection buttons
        6. Send message

    Example Output:
        📊 Your Positions (Page 1/3)

        1. Will Trump win 2024?
           ✅ Yes • 100.0 shares • $72.50

        2. Bitcoin above $50k by Jan 2025?
           ❌ No • 50.0 shares • $28.00

        ...

        [⬅️ Previous] [Page 1/3] [Next ➡️]
        [Select Position #1] [Select Position #2] ...
    """
```

**Service Calls**:
- `user_wallet_service.get_user_wallet(telegram_user_id)` → UserWallet
- `position_service.get_positions(wallet)` → List[Position]
- `PaginationHelper.paginate(positions, page=1, page_size=10)` → PaginatedData[Position]

**Empty List Handling** (per FR-007):
```python
if not positions:
    await update.message.reply_text(
        "📊 Your Positions\n\n"
        "No active positions found.\n\n"
        "Use /markets to browse markets."
    )
    return
```

**Formatting**:
```python
def format_position_summary(position: Position, index: int) -> str:
    """Format single position for list view."""
    market_name = position.market_question[:40] + "..." if len(position.market_question) > 40 else position.market_question
    outcome_emoji = "✅" if position.outcome == "Yes" else "❌"
    return (
        f"{index}. {market_name}\n"
        f"   {outcome_emoji} {position.outcome} • {position.size:.1f} shares • ${position.value:.2f}\n"
    )
```

---

### 2. position_page_callback

**Signature**:
```python
async def position_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle pagination callback for positions list.

    Callback data format: "pos_page_{page_number}"

    Args:
        update: Telegram callback query with page number.
        context: Bot context.

    Returns:
        None

    Flow:
        1. Parse page number from callback_data
        2. Re-fetch positions
        3. Paginate to requested page
        4. Edit message with new page content
    """
```

**Callback Data Parsing**:
```python
query = update.callback_query
await query.answer()

# Parse "pos_page_3" → page=3
page = int(query.data.split("_")[-1])
```

---

### 3. position_select_callback

**Signature**:
```python
async def position_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle position selection callback.

    Callback data format: "pos_select_{index}"

    Shows position details and action buttons (redeem, market sell, limit sell).

    Args:
        update: Telegram callback query with position index.
        context: Bot context.

    Returns:
        None

    Flow:
        1. Parse position index from callback_data
        2. Re-fetch positions to get selected position
        3. Check if position is redeemable (market finalized + winning outcome)
        4. Display position details
        5. Show action buttons based on redeemability

    Example Output (redeemable):
        🎯 Position Details

        Market: Will Trump win 2024?
        Outcome: ✅ Yes
        Shares: 100.0
        Current Value: $72.50
        Average Cost: $0.65 per share

        Market Status: Finalized
        Winning Outcome: Yes ✅

        [🎁 Redeem Winnings] [🔙 Back]

    Example Output (not redeemable):
        🎯 Position Details

        Market: Will Trump win 2024?
        Outcome: ✅ Yes
        Shares: 100.0
        Current Value: $72.50

        Market Status: Active

        [💰 Market Sell] [📈 Limit Sell] [🔙 Back]
    """
```

**Service Calls**:
- `position_service.get_positions(wallet)` → List[Position]
- `position_service.is_position_redeemable(position)` → bool

**Button Logic**:
```python
if position.is_redeemable:
    buttons = [
        [InlineKeyboardButton("🎁 Redeem Winnings", callback_data=f"pos_redeem_{position.token_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="pos_list")]
    ]
else:
    buttons = [
        [InlineKeyboardButton("💰 Market Sell", callback_data=f"pos_sell_market_{position.token_id}")],
        [InlineKeyboardButton("📈 Limit Sell", callback_data=f"pos_sell_limit_{position.token_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="pos_list")]
    ]
```

---

### 4. position_redeem_callback

**Signature**:
```python
async def position_redeem_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle position redemption callback.

    Callback data format: "pos_redeem_{token_id}"

    Args:
        update: Telegram callback query with token ID.
        context: Bot context.

    Returns:
        None

    Flow:
        1. Parse token_id from callback_data
        2. Get user wallet
        3. Call position_service.redeem_position(wallet, token_id)
        4. Display success or error message

    Example Output (success):
        ✅ Redemption Successful

        Market: Will Trump win 2024?
        Redeemed: 100.0 shares
        Amount: $100.00 USDC

        Transaction: 0x1234...5678

        Funds added to your wallet balance.

    Example Output (error):
        ❌ Redemption Failed

        Error: Market not yet finalized.

        Please wait for market resolution.
    """
```

**Service Calls**:
- `user_wallet_service.get_user_wallet(telegram_user_id)` → UserWallet
- `position_service.redeem_position(wallet, token_id)` → dict (tx_hash, amount)

---

## OrderHandler

**Module**: `poly_boost.bot.handlers.order_handler`
**Commands**: `/orders`
**Callbacks**: `order_page_{page}`, `order_select_{index}`, `order_cancel_{order_id}`

### 1. orders_command

**Signature**:
```python
async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /orders command - display paginated active orders list.

    Args:
        update: Telegram update containing command.
        context: Bot context.

    Returns:
        None

    Example Output:
        📋 Active Orders (Page 1/2)

        1. Will Trump win 2024?
           BUY Yes @ $0.72 • 50.0 shares

        2. Bitcoin above $50k by Jan 2025?
           SELL No @ $0.45 • 100.0 shares

        ...

        [Select Order #1] [Select Order #2] ...
        [⬅️ Previous] [Page 1/2] [Next ➡️]
    """
```

**Service Calls**:
- `user_wallet_service.get_user_wallet(telegram_user_id)` → UserWallet
- `order_service.get_orders(wallet)` → List[Order]

**Empty List Handling** (per FR-007):
```python
if not orders:
    await update.message.reply_text(
        "📋 Active Orders\n\n"
        "No active orders found."
    )
    return
```

---

### 2. order_cancel_callback

**Signature**:
```python
async def order_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle order cancellation callback.

    Callback data format: "order_cancel_{order_id}"

    Args:
        update: Telegram callback query with order ID.
        context: Bot context.

    Returns:
        None

    Example Output (success):
        ✅ Order Cancelled

        Order ID: 0x1234...5678
        Market: Will Trump win 2024?

    Example Output (error):
        ❌ Cancellation Failed

        Error: Order already filled.
    """
```

**Service Calls**:
- `user_wallet_service.get_user_wallet(telegram_user_id)` → UserWallet
- `order_service.cancel_order(wallet, order_id)` → bool

---

## ActivityHandler

**Module**: `poly_boost.bot.handlers.activity_handler`
**Commands**: `/activities`
**Callbacks**: `activity_page_{page}`

### 1. activities_command

**Signature**:
```python
async def activities_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /activities command - display paginated activity history.

    Args:
        update: Telegram update containing command.
        context: Bot context.

    Returns:
        None

    Example Output:
        📜 Activity History (Page 1/5)

        1. BUY • 2025-11-05 14:32
           Will Trump win 2024? (Yes)
           50.0 shares @ $0.72 • Total: $36.00

        2. SELL • 2025-11-05 12:15
           Bitcoin above $50k? (No)
           100.0 shares @ $0.45 • Total: $45.00

        ...

        [⬅️ Previous] [Page 1/5] [Next ➡️]
    """
```

**Service Calls**:
- `user_wallet_service.get_user_wallet(telegram_user_id)` → UserWallet
- `activity_service.get_activity(wallet, limit=100)` → List[Activity]

**Empty List Handling** (per FR-007):
```python
if not activities:
    await update.message.reply_text(
        "📜 Activity History\n\n"
        "No activity found."
    )
    return
```

---

## WalletInitConversation

**Module**: `poly_boost.bot.conversations.wallet_init`
**Pattern**: ConversationHandler for multi-step wallet initialization

### States

```python
WALLET_CHOICE = 0  # User chooses generate or import
INPUT_PRIVATE_KEY = 1  # User inputs private key for import
```

### 1. wallet_choice_callback

**Signature**:
```python
async def wallet_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle wallet generation or import choice.

    Callback data: "wallet_generate" or "wallet_import"

    Args:
        update: Telegram callback query with choice.
        context: Bot context.

    Returns:
        ConversationHandler state (INPUT_PRIVATE_KEY or END).

    Flow (Generate):
        1. Generate new EOA wallet (eth_account.Account.create())
        2. Store in database via user_wallet_service
        3. Display address and private key with warning
        4. END conversation

    Flow (Import):
        1. Prompt user for private key input
        2. Return INPUT_PRIVATE_KEY state

    Example Output (Generate):
        ✅ Wallet Created

        Address: `0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B`

        ⚠️ SAVE YOUR PRIVATE KEY:
        `0x1234...5678...abcd`

        Keep this key safe! If lost, you cannot recover your wallet.

    Example Output (Import):
        📥 Import Wallet

        Please send your private key.

        Format: 0x followed by 64 hex characters

        ⚠️ Your message will be deleted after processing for security.
    """
```

**Service Calls**:
- `user_wallet_service.create_user_wallet(...)` → UserWallet

**Private Key Generation**:
```python
from eth_account import Account

account = Account.create()
wallet_address = account.address
private_key = account.key.hex()
```

---

### 2. receive_private_key

**Signature**:
```python
async def receive_private_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle private key input for wallet import.

    Args:
        update: Telegram message with private key.
        context: Bot context.

    Returns:
        ConversationHandler state (INPUT_PRIVATE_KEY for retry, END for success).

    Flow:
        1. Parse private key from message
        2. Validate format (0x + 64 hex chars)
        3. Derive address from private key
        4. Store in database
        5. Delete user's message containing private key (FR-004)
        6. Display success message with address
        7. END conversation

    Example Output (success):
        ✅ Wallet Imported

        Address: `0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B`

        Your wallet is ready to use.
        Use /wallet to view details.

    Example Output (error):
        ❌ Invalid Private Key

        Please check the format and try again.

        Format: 0x followed by 64 hex characters
        Example: 0x1234...5678...abcd

        Send /cancel to abort.
    """
```

**Service Calls**:
- `user_wallet_service.create_user_wallet(...)` → UserWallet

**Private Key Validation**:
```python
from eth_account import Account

try:
    private_key = update.message.text.strip()
    account = Account.from_key(private_key)
    wallet_address = account.address

    # Store wallet
    user_wallet_service.create_user_wallet(
        telegram_user_id=update.effective_user.id,
        wallet_address=wallet_address,
        private_key=private_key
    )

    # Delete message containing private key (FR-004)
    await update.message.delete()

    # Success message
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"✅ Wallet Imported\n\nAddress: `{wallet_address}`",
        parse_mode="Markdown"
    )

    return ConversationHandler.END

except ValueError:
    await update.message.reply_text("❌ Invalid private key format. Please try again.")
    return INPUT_PRIVATE_KEY
```

---

### 3. cancel_conversation

**Signature**:
```python
async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle /cancel command during wallet initialization.

    Args:
        update: Telegram update.
        context: Bot context.

    Returns:
        ConversationHandler.END

    Example Output:
        Wallet setup cancelled.

        Use /start to try again.
    """
```

---

## ConversationHandler Registration

```python
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters

wallet_init_conversation = ConversationHandler(
    entry_points=[CommandHandler("start", start_command)],
    states={
        WALLET_CHOICE: [
            CallbackQueryHandler(wallet_choice_callback, pattern="^wallet_(generate|import)$")
        ],
        INPUT_PRIVATE_KEY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_private_key)
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_conversation)],
    conversation_timeout=300  # 5 minutes
)
```

---

## Error Handling Patterns

### Network Errors (per FR-017)

```python
try:
    positions = position_service.get_positions(wallet)
except NetworkError as e:
    logger.error(f"Network error fetching positions", extra={
        "telegram_user_id": update.effective_user.id,
        "error": str(e)
    })
    await update.message.reply_text(
        "❌ Network error. Please try again.\n\n"
        "If the problem persists, check your internet connection."
    )
    # Clear stale data per FR-017
    context.user_data.pop('positions', None)
    return
```

### Service Errors

```python
try:
    result = service.some_operation(...)
except ValueError as e:
    # User input error
    await update.message.reply_text(f"❌ {str(e)}")
except Exception as e:
    # Unexpected error
    logger.error(f"Unexpected error", exc_info=True)
    await update.message.reply_text(
        "❌ An error occurred. Please try again later."
    )
```

---

## Logging Strategy

**Log Format**:
```python
logger.info("User executed command", extra={
    "telegram_user_id": update.effective_user.id,
    "command": update.message.text,
    "timestamp": datetime.now().isoformat()
})

logger.error("Service call failed", extra={
    "telegram_user_id": update.effective_user.id,
    "service": "PositionService",
    "method": "get_positions",
    "error": str(e)
}, exc_info=True)
```

**Never Log**:
- Private keys
- Full wallet addresses in error messages (use `address[:10]...address[-8:]`)

---

## Testing Contract

**Unit Tests**:
- Mock all service calls (UserWalletService, PositionService, etc.)
- Mock Telegram update and context objects
- Test each handler function independently

**Integration Tests**:
- Test full conversation flows (wallet initialization)
- Mock Telegram API responses
- Verify message formatting and keyboard layouts

**Example Test**:
```python
from unittest.mock import Mock, AsyncMock
import pytest

@pytest.mark.asyncio
async def test_positions_command_empty_list():
    """Test /positions command with no positions."""
    # Mock update and context
    update = Mock()
    update.effective_user.id = 123456789
    update.message.reply_text = AsyncMock()

    context = Mock()
    context.bot_data = {
        'user_wallet_service': Mock(),
        'position_service': Mock()
    }

    # Mock service responses
    context.bot_data['user_wallet_service'].get_user_wallet.return_value = Mock(to_wallet=Mock())
    context.bot_data['position_service'].get_positions.return_value = []

    # Call handler
    await positions_command(update, context)

    # Verify empty message sent
    update.message.reply_text.assert_called_once()
    args = update.message.reply_text.call_args[0]
    assert "No active positions" in args[0]
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-05 | Initial contract definition |
