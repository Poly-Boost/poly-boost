"""
Activity history handlers for Telegram bot.

Handles activity-related commands and callbacks:
- /activities: Display paginated activity history
- Activity pagination: Navigate through pages
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from poly_boost.services.user_wallet_service import UserWalletService
from poly_boost.bot.utils.pagination import PaginationHelper

logger = logging.getLogger(__name__)


async def activities_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /activities command - display paginated activity history.

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

        # Get activity service
        activity_service = context.bot_data.get('activity_service')
        if not activity_service:
            await update.message.reply_text(
                "⚠️ Service temporarily unavailable. Try again later."
            )
            return

        # Get activities (limit to 100 most recent)
        activities = activity_service.get_activity(wallet_obj, limit=100)

        # Handle empty list (FR-007)
        if not activities:
            await update.message.reply_text(
                "📜 *Activity History*\n\n"
                "No activity found.",
                parse_mode="Markdown"
            )
            return

        # Store activities in user_data for later access
        context.user_data['activities'] = activities

        # Paginate activities
        page = 1
        paginated = PaginationHelper.paginate(activities, page=page, page_size=10)

        # Format message
        message = format_activities_message(paginated)

        # Create pagination keyboard
        keyboard = PaginationHelper.create_pagination_keyboard(
            paginated,
            callback_prefix="activity_page"
        )

        await update.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in activities_command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Network error. Please try again.\n\n"
            "If the problem persists, check your internet connection."
        )
        # Clear stale data per FR-017
        context.user_data.pop('activities', None)


async def activity_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle pagination callback for activity history.

    Callback data format: "activity_page_{page_number}"

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

        # Get activities from user_data
        activities = context.user_data.get('activities', [])
        if not activities:
            await query.edit_message_text(
                "Session expired. Please use /activities to refresh."
            )
            return

        # Paginate to requested page
        paginated = PaginationHelper.paginate(activities, page=page, page_size=10)

        # Format message
        message = format_activities_message(paginated)

        # Create pagination keyboard
        keyboard = PaginationHelper.create_pagination_keyboard(
            paginated,
            callback_prefix="activity_page"
        )

        await query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in activity_page_callback: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ An error occurred. Please use /activities to refresh."
        )


def format_activities_message(paginated_data) -> str:
    """
    Format paginated activities list message.

    Args:
        paginated_data: PaginatedData[Activity] instance

    Returns:
        Formatted message string
    """
    message = f"📜 *Activity History* (Page {paginated_data.page}/{paginated_data.total_pages})\n\n"

    for i, activity in enumerate(paginated_data.items):
        global_index = (paginated_data.page - 1) * paginated_data.page_size + i

        # Format activity type
        activity_type = activity.type
        type_emoji = get_activity_type_emoji(activity_type)

        # Format timestamp
        timestamp = format_timestamp(activity.timestamp)

        # Get market name (truncate if too long)
        market_name = getattr(activity, 'market_question', 'Unknown Market')
        if market_name and len(market_name) > 35:
            market_name = market_name[:35] + "..."

        # Format activity details based on type
        if activity_type == "TRADE":
            side = getattr(activity, 'side', 'UNKNOWN')
            outcome = getattr(activity, 'outcome', 'Unknown')
            size = getattr(activity, 'tokens', 0)
            price = getattr(activity, 'price', 0)
            total = getattr(activity, 'usdc_size', 0)

            message += (
                f"{global_index + 1}. {type_emoji} {activity_type} • {timestamp}\n"
                f"   {market_name}\n"
                f"   {side} {outcome} • {size:.1f} @ ${price:.2f} • Total: ${total:.2f}\n\n"
            )
        elif activity_type == "REDEEM":
            outcome = getattr(activity, 'outcome', 'Unknown')
            size = getattr(activity, 'tokens', 0)
            total = getattr(activity, 'usdc_size', 0)

            message += (
                f"{global_index + 1}. {type_emoji} {activity_type} • {timestamp}\n"
                f"   {market_name}\n"
                f"   {outcome} • {size:.1f} shares • ${total:.2f}\n\n"
            )
        else:
            # Generic format for other types
            size = getattr(activity, 'tokens', 0)
            total = getattr(activity, 'usdc_size', 0)

            message += (
                f"{global_index + 1}. {type_emoji} {activity_type} • {timestamp}\n"
                f"   {market_name}\n"
                f"   {size:.1f} • ${total:.2f}\n\n"
            )

    return message


def get_activity_type_emoji(activity_type: str) -> str:
    """
    Get emoji for activity type.

    Args:
        activity_type: Activity type string

    Returns:
        Emoji string
    """
    emoji_map = {
        "TRADE": "💱",
        "SPLIT": "✂️",
        "MERGE": "🔗",
        "REDEEM": "🎁",
        "REWARD": "🏆",
        "CONVERSION": "🔄"
    }
    return emoji_map.get(activity_type, "📌")


def format_timestamp(timestamp: int) -> str:
    """
    Format Unix timestamp to human-readable string.

    Args:
        timestamp: Unix timestamp in seconds

    Returns:
        Formatted date string
    """
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "Unknown time"
