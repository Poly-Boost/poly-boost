"""
Order management handlers for Telegram bot.

Handles order-related commands and callbacks:
- /orders: Display paginated active orders list
- Order selection: Show order details with cancel button
- Order cancellation: Execute order cancellation
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from poly_boost.services.user_wallet_service import UserWalletService
from poly_boost.bot.utils.pagination import PaginationHelper

logger = logging.getLogger(__name__)


async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /orders command - display paginated active orders list.

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

        # Create order service for this wallet
        from poly_boost.core.client_factory import ClientFactory
        client_factory: ClientFactory = context.bot_data.get('client_factory')

        if not client_factory:
            await update.message.reply_text(
                "⚠️ Service temporarily unavailable. Try again later."
            )
            return

        # Get wallet-specific clients
        clob_client, web3_client = client_factory.create_clients(wallet_obj)

        # Import OrderService
        from poly_boost.services.order_service import OrderService
        order_service = OrderService(wallet_obj, clob_client, web3_client)

        # Get active orders
        orders = order_service.get_orders()

        # Handle empty list (FR-007)
        if not orders:
            await update.message.reply_text(
                "📋 *Active Orders*\n\n"
                "No active orders found.",
                parse_mode="Markdown"
            )
            return

        # Store orders in user_data for later access
        context.user_data['orders'] = orders

        # Paginate orders
        page = 1
        paginated = PaginationHelper.paginate(orders, page=page, page_size=10)

        # Format message
        message = format_orders_message(paginated)

        # Create buttons (selection + pagination)
        buttons = create_order_selection_buttons(paginated, page)

        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in orders_command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Network error. Please try again.\n\n"
            "If the problem persists, check your internet connection."
        )
        # Clear stale data per FR-017
        context.user_data.pop('orders', None)


async def order_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle pagination callback for orders list.

    Callback data format: "order_page_{page_number}"

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

        # Get orders from user_data
        orders = context.user_data.get('orders', [])
        if not orders:
            await query.edit_message_text(
                "Session expired. Please use /orders to refresh."
            )
            return

        # Paginate to requested page
        paginated = PaginationHelper.paginate(orders, page=page, page_size=10)

        # Format message
        message = format_orders_message(paginated)

        # Create buttons
        buttons = create_order_selection_buttons(paginated, page)

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in order_page_callback: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ An error occurred. Please use /orders to refresh."
        )


async def order_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle order selection callback.

    Callback data format: "order_select_{index}"

    Shows order details and cancel button.

    Args:
        update: Telegram callback query with order index.
        context: Bot context.

    Returns:
        None
    """
    query = update.callback_query
    await query.answer()

    try:
        # Parse order index from callback_data
        index = int(query.data.split("_")[-1])

        # Get orders from user_data
        orders = context.user_data.get('orders', [])
        if not orders or index >= len(orders):
            await query.edit_message_text(
                "Order not found. Please use /orders to refresh."
            )
            return

        order = orders[index]

        # Format order details
        message = format_order_detail(order)

        # Create action buttons
        buttons = create_order_action_buttons(order)

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in order_select_callback: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ An error occurred. Please use /orders to refresh."
        )


async def order_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle order cancellation callback.

    Callback data format: "order_cancel_{order_id}"

    Args:
        update: Telegram callback query with order ID.
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
        # Parse order_id from callback_data (everything after "order_cancel_")
        order_id = query.data.replace("order_cancel_", "")

        # Get user wallet
        user_wallet = user_wallet_service.get_user_wallet(user_id)
        if not user_wallet:
            await query.edit_message_text(
                "Please initialize your wallet with /start first."
            )
            return

        wallet_obj = user_wallet.to_wallet()

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

        # Get order details for display
        orders = context.user_data.get('orders', [])
        order = next((o for o in orders if o.get('order_id') == order_id), None)

        # Cancel order
        await query.edit_message_text(
            f"⏳ Cancelling order...\n\n"
            f"Order ID: {order_id[:8]}..."
        )

        result = order_service.cancel_order(order_id)

        # Format success message
        message = f"✅ *Order Cancelled*\n\n"
        message += f"Order ID: `{order_id[:10]}...{order_id[-8:]}`\n"

        if order:
            market_name = order.get('market_name', 'Unknown')
            if market_name:
                message += f"Market: {market_name[:50]}\n"

        await query.edit_message_text(
            message,
            parse_mode="Markdown"
        )

        # Clear cached orders
        context.user_data.pop('orders', None)

    except Exception as e:
        logger.error(f"Error cancelling order: {e}", exc_info=True)
        await query.edit_message_text(
            f"❌ *Cancellation Failed*\n\n"
            f"Error: {str(e)}\n\n"
            f"The order may have already been filled or cancelled.",
            parse_mode="Markdown"
        )


async def order_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle "Back to list" callback.

    Callback data: "order_list"

    Args:
        update: Telegram callback query.
        context: Bot context.

    Returns:
        None
    """
    query = update.callback_query
    await query.answer()

    try:
        # Get orders from user_data
        orders = context.user_data.get('orders', [])
        if not orders:
            await query.edit_message_text(
                "Session expired. Please use /orders to refresh."
            )
            return

        # Show first page
        page = 1
        paginated = PaginationHelper.paginate(orders, page=page, page_size=10)

        # Format message
        message = format_orders_message(paginated)

        # Create buttons
        buttons = create_order_selection_buttons(paginated, page)

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in order_list_callback: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ An error occurred. Please use /orders to refresh."
        )


def format_orders_message(paginated_data) -> str:
    """
    Format paginated orders list message.

    Args:
        paginated_data: PaginatedData[dict] instance

    Returns:
        Formatted message string
    """
    message = f"📋 *Active Orders* (Page {paginated_data.page}/{paginated_data.total_pages})\n\n"

    for i, order in enumerate(paginated_data.items):
        global_index = (paginated_data.page - 1) * paginated_data.page_size + i

        # Get order details
        market_name = order.get('market_name', 'Unknown Market')
        if market_name and len(market_name) > 40:
            market_name = market_name[:40] + "..."

        side = order.get('side', 'UNKNOWN')
        outcome = order.get('outcome', 'Unknown')
        price = float(order.get('price', 0))
        size = float(order.get('original_size', 0))

        side_emoji = "🟢" if side == "BUY" else "🔴"

        message += (
            f"{global_index + 1}. {market_name}\n"
            f"   {side_emoji} {side} {outcome} @ ${price:.2f} • {size:.1f} shares\n\n"
        )

    return message


def format_order_detail(order: dict) -> str:
    """
    Format order detail message.

    Args:
        order: Order dictionary

    Returns:
        Formatted message string
    """
    # Get order details
    order_id = order.get('order_id', 'Unknown')
    market_name = order.get('market_name', 'Unknown Market')
    side = order.get('side', 'UNKNOWN')
    outcome = order.get('outcome', 'Unknown')
    price = float(order.get('price', 0))
    size = float(order.get('size_matched', 0))
    original_size = float(order.get('original_size', 0))
    status = order.get('status', 'UNKNOWN')

    side_emoji = "🟢" if side == "BUY" else "🔴"

    message = (
        f"📋 *Order Details*\n\n"
        f"Market: {market_name}\n"
        f"Order ID: `{order_id[:10]}...{order_id[-8:]}`\n\n"
        f"Side: {side_emoji} {side}\n"
        f"Outcome: {outcome}\n"
        f"Price: ${price:.2f}\n"
        f"Size: {original_size:.1f} shares\n"
        f"Filled: {size:.1f} shares\n"
        f"Status: {status}\n"
    )

    return message


def create_order_selection_buttons(paginated_data, page: int) -> list:
    """
    Create inline keyboard with order selection and pagination buttons.

    Args:
        paginated_data: PaginatedData[dict] instance
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
                callback_data=f"order_select_{global_index}"
            )
        )

    # Split into rows of 2
    for i in range(0, len(selection_buttons), 2):
        buttons.append(selection_buttons[i:i+2])

    # Add pagination buttons if needed
    if not paginated_data.is_single_page():
        pagination_keyboard = PaginationHelper.create_pagination_keyboard(
            paginated_data,
            callback_prefix="order_page"
        )
        buttons.extend(pagination_keyboard.inline_keyboard)

    return buttons


def create_order_action_buttons(order: dict) -> list:
    """
    Create action buttons for order detail view.

    Args:
        order: Order dictionary

    Returns:
        List of button rows
    """
    buttons = []

    # Cancel button
    order_id = order.get('order_id', '')
    buttons.append([
        InlineKeyboardButton(
            "❌ Cancel Order",
            callback_data=f"order_cancel_{order_id}"
        )
    ])

    # Back button
    buttons.append([
        InlineKeyboardButton("🔙 Back to List", callback_data="order_list")
    ])

    return buttons
