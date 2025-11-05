"""
Position management handlers for Telegram bot.

Handles position-related commands and callbacks:
- /positions: Display paginated positions list
- Position selection: Show position details with action buttons
- Redeem/Sell actions: Execute position operations
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from poly_boost.services.user_wallet_service import UserWalletService
from poly_boost.bot.utils.pagination import PaginationHelper

logger = logging.getLogger(__name__)


async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /positions command - display paginated positions list.

    Args:
        update: Telegram update containing command.
        context: Bot context.

    Returns:
        None
    """
    user_id = update.effective_user.id
    user_wallet_service: UserWalletService = context.bot_data.get('user_wallet_service')

    if not user_wallet_service:
        await update.message.reply_text(
            "⚠️ Service temporarily unavailable. Try again later."
        )
        return

    try:
        # Check if user has wallet
        user_wallet = user_wallet_service.get_user_wallet(user_id)
        if not user_wallet:
            await update.message.reply_text(
                "Please initialize your wallet with /start first."
            )
            return

        wallet_obj = user_wallet.to_wallet()

        # Get positions from service
        position_service = context.bot_data.get('position_service')
        if not position_service:
            await update.message.reply_text(
                "⚠️ Service temporarily unavailable. Try again later."
            )
            return

        positions = position_service.get_positions(wallet_obj)

        # Handle empty list (FR-007)
        if not positions:
            await update.message.reply_text(
                "📊 *Your Positions*\n\n"
                "No active positions found.\n\n"
                "Use /markets to browse markets.",
                parse_mode="Markdown"
            )
            return

        # Store positions in user_data for later access
        context.user_data['positions'] = positions

        # Paginate positions
        page = 1
        paginated = PaginationHelper.paginate(positions, page=page, page_size=10)

        # Format message
        message = format_positions_message(paginated)

        # Create buttons (selection + pagination)
        buttons = create_position_selection_buttons(paginated, page)

        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in positions_command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Network error. Please try again.\n\n"
            "If the problem persists, check your internet connection."
        )
        # Clear stale data per FR-017
        context.user_data.pop('positions', None)


async def position_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle pagination callback for positions list.

    Callback data format: "pos_page_{page_number}"

    Args:
        update: Telegram callback query with page number.
        context: Bot context.

    Returns:
        None
    """
    query = update.callback_query
    await query.answer()

    try:
        # Parse page number from callback_data
        page = int(query.data.split("_")[-1])

        # Get positions from user_data
        positions = context.user_data.get('positions', [])
        if not positions:
            await query.edit_message_text(
                "Session expired. Please use /positions to refresh."
            )
            return

        # Paginate to requested page
        paginated = PaginationHelper.paginate(positions, page=page, page_size=10)

        # Format message
        message = format_positions_message(paginated)

        # Create buttons
        buttons = create_position_selection_buttons(paginated, page)

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in position_page_callback: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ An error occurred. Please use /positions to refresh."
        )


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
    """
    query = update.callback_query
    await query.answer()

    try:
        # Parse position index from callback_data
        index = int(query.data.split("_")[-1])

        # Get positions from user_data
        positions = context.user_data.get('positions', [])
        if not positions or index >= len(positions):
            await query.edit_message_text(
                "Position not found. Please use /positions to refresh."
            )
            return

        position = positions[index]

        # Format position details
        message = format_position_detail(position)

        # Create action buttons based on redeemability
        buttons = create_position_action_buttons(position, index)

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in position_select_callback: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ An error occurred. Please use /positions to refresh."
        )


async def position_redeem_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle position redemption callback.

    Callback data format: "pos_redeem_{token_id}"

    Args:
        update: Telegram callback query with token ID.
        context: Bot context.

    Returns:
        None
    """
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_wallet_service: UserWalletService = context.bot_data.get('user_wallet_service')

    if not user_wallet_service:
        await query.edit_message_text(
            "⚠️ Service temporarily unavailable. Try again later."
        )
        return

    try:
        # Parse token_id from callback_data
        token_id = query.data.split("_")[-1]

        # Get user wallet
        user_wallet = user_wallet_service.get_user_wallet(user_id)
        if not user_wallet:
            await query.edit_message_text(
                "Please initialize your wallet with /start first."
            )
            return

        wallet_obj = user_wallet.to_wallet()

        # Get position details
        positions = context.user_data.get('positions', [])
        position = next((p for p in positions if p.token_id == token_id), None)

        if not position:
            await query.edit_message_text(
                "Position not found. Please use /positions to refresh."
            )
            return

        # Create order service for this wallet
        from poly_boost.core.client_factory import ClientFactory
        client_factory: ClientFactory = context.bot_data.get('client_factory')

        if not client_factory:
            await query.edit_message_text(
                "⚠️ Service temporarily unavailable. Try again later."
            )
            return

        # Get wallet-specific clients
        clob_client, web3_client = client_factory.create_clients(wallet_obj)

        # Import OrderService
        from poly_boost.services.order_service import OrderService
        order_service = OrderService(wallet_obj, clob_client, web3_client)

        # Redeem position
        await query.edit_message_text(
            f"⏳ Redeeming position...\n\n"
            f"Market: {position.market_question[:50]}...\n"
            f"Shares: {position.size:.2f}"
        )

        result = order_service.claim_rewards(
            condition_id=position.condition_id,
            token_id=token_id,
            amount=position.size
        )

        # Format success message
        tx_hash = result.get('tx_hash', '')
        amounts = result.get('amounts', [])
        redeemed_amount = sum(amounts)

        await query.edit_message_text(
            f"✅ *Redemption Successful*\n\n"
            f"Market: {position.market_question[:50]}...\n"
            f"Redeemed: {redeemed_amount:.2f} shares\n"
            f"Amount: ${redeemed_amount:.2f} USDC\n\n"
            f"Transaction: `{tx_hash[:10]}...{tx_hash[-8:]}`\n\n"
            f"Funds added to your wallet balance.",
            parse_mode="Markdown"
        )

        # Clear cached positions
        context.user_data.pop('positions', None)

    except Exception as e:
        logger.error(f"Error redeeming position: {e}", exc_info=True)
        await query.edit_message_text(
            f"❌ *Redemption Failed*\n\n"
            f"Error: {str(e)}\n\n"
            f"Please try again or contact support.",
            parse_mode="Markdown"
        )


async def position_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle "Back to list" callback.

    Callback data: "pos_list"

    Args:
        update: Telegram callback query.
        context: Bot context.

    Returns:
        None
    """
    query = update.callback_query
    await query.answer()

    try:
        # Get positions from user_data
        positions = context.user_data.get('positions', [])
        if not positions:
            await query.edit_message_text(
                "Session expired. Please use /positions to refresh."
            )
            return

        # Show first page
        page = 1
        paginated = PaginationHelper.paginate(positions, page=page, page_size=10)

        # Format message
        message = format_positions_message(paginated)

        # Create buttons
        buttons = create_position_selection_buttons(paginated, page)

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in position_list_callback: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ An error occurred. Please use /positions to refresh."
        )


def format_positions_message(paginated_data) -> str:
    """
    Format paginated positions list message.

    Args:
        paginated_data: PaginatedData[Position] instance

    Returns:
        Formatted message string
    """
    message = f"📊 *Your Positions* (Page {paginated_data.page}/{paginated_data.total_pages})\n\n"

    for i, position in enumerate(paginated_data.items):
        global_index = (paginated_data.page - 1) * paginated_data.page_size + i

        # Truncate market name
        market_name = position.market_question[:40]
        if len(position.market_question) > 40:
            market_name += "..."

        outcome_emoji = "✅" if position.outcome == "Yes" else "❌"

        message += (
            f"{global_index + 1}. {market_name}\n"
            f"   {outcome_emoji} {position.outcome} • {position.size:.1f} shares • ${position.value:.2f}\n\n"
        )

    return message


def format_position_detail(position) -> str:
    """
    Format position detail message.

    Args:
        position: Position object

    Returns:
        Formatted message string
    """
    outcome_emoji = "✅" if position.outcome == "Yes" else "❌"

    # Check if redeemable
    is_redeemable = getattr(position, 'redeemable', False)
    market_status = "Finalized" if is_redeemable else "Active"

    message = (
        f"🎯 *Position Details*\n\n"
        f"Market: {position.market_question}\n"
        f"Outcome: {outcome_emoji} {position.outcome}\n"
        f"Shares: {position.size:.2f}\n"
        f"Current Value: ${position.value:.2f}\n"
    )

    # Add average cost if available
    if hasattr(position, 'avg_price') and position.avg_price:
        message += f"Average Cost: ${position.avg_price:.2f} per share\n"

    message += f"\nMarket Status: {market_status}\n"

    if is_redeemable:
        message += "\n✅ This position is redeemable!"

    return message


def create_position_selection_buttons(paginated_data, page: int) -> list:
    """
    Create inline keyboard with position selection and pagination buttons.

    Args:
        paginated_data: PaginatedData[Position] instance
        page: Current page number

    Returns:
        List of button rows
    """
    buttons = []

    # Add selection buttons (2 per row)
    selection_buttons = []
    for i in range(len(paginated_data.items)):
        global_index = (page - 1) * 10 + i
        selection_buttons.append(
            InlineKeyboardButton(
                f"#{global_index + 1}",
                callback_data=f"pos_select_{global_index}"
            )
        )

    # Split into rows of 2
    for i in range(0, len(selection_buttons), 2):
        buttons.append(selection_buttons[i:i+2])

    # Add pagination buttons if needed
    if not paginated_data.is_single_page():
        pagination_keyboard = PaginationHelper.create_pagination_keyboard(
            paginated_data,
            callback_prefix="pos_page"
        )
        buttons.extend(pagination_keyboard.inline_keyboard)

    return buttons


def create_position_action_buttons(position, index: int) -> list:
    """
    Create action buttons based on position redeemability.

    Args:
        position: Position object
        index: Position index in list

    Returns:
        List of button rows
    """
    buttons = []

    # Check if redeemable
    is_redeemable = getattr(position, 'redeemable', False)

    if is_redeemable:
        buttons.append([
            InlineKeyboardButton(
                "🎁 Redeem Winnings",
                callback_data=f"pos_redeem_{position.token_id}"
            )
        ])
    else:
        buttons.append([
            InlineKeyboardButton(
                "💰 Market Sell",
                callback_data=f"pos_sell_market_{position.token_id}"
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                "📈 Limit Sell",
                callback_data=f"pos_sell_limit_{position.token_id}"
            )
        ])

    # Back button
    buttons.append([
        InlineKeyboardButton("🔙 Back to List", callback_data="pos_list")
    ])

    return buttons


# Legacy handlers for backward compatibility
async def show_positions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Legacy handler - redirects to positions_command."""
    await positions_command(update, context)


async def view_all_positions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Legacy handler - redirects to position_page_callback."""
    await position_page_callback(update, context)


async def view_position_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Legacy handler for position value view."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_wallet_service: UserWalletService = context.bot_data.get('user_wallet_service')

    if not user_wallet_service:
        await query.edit_message_text(
            "⚠️ Service temporarily unavailable. Try again later."
        )
        return

    try:
        user_wallet = user_wallet_service.get_user_wallet(user_id)
        if not user_wallet:
            await query.edit_message_text(
                "Please initialize your wallet with /start first."
            )
            return

        wallet_obj = user_wallet.to_wallet()
        position_service = context.bot_data.get('position_service')

        if not position_service:
            await query.edit_message_text(
                "⚠️ Service temporarily unavailable. Try again later."
            )
            return

        value = position_service.get_position_value(wallet_obj)

        message = (
            f"💰 *Total Position Value*\n\n"
            f"Wallet: `{user_wallet.wallet_address[:10]}...{user_wallet.wallet_address[-8:]}`\n"
            f"Total Value: ${float(value):.2f} USDC"
        )

        await query.edit_message_text(
            message,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error getting position value: {e}", exc_info=True)
        await query.edit_message_text(
            f"❌ Error: {str(e)}"
        )
