"""
Copy trading control handlers for Telegram bot.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from poly_boost.bot.keyboards import get_trading_menu_keyboard


logger = logging.getLogger(__name__)


async def show_trading_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show copy trading control menu.

    Args:
        update: Telegram update
        context: Bot context
    """
    await update.message.reply_text(
        "🔄 *Copy Trading Control*\n\n"
        "Manage your copy trading operations:",
        parse_mode="Markdown",
        reply_markup=get_trading_menu_keyboard()
    )


async def view_trading_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    View copy trading status.

    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    await query.answer()

    try:
        trading_service = context.bot_data['trading_service']
        status = trading_service.get_copy_trading_status()

        total_traders = status['total_traders']
        active_subs = status['active_subscriptions']

        message = (
            f"🔄 *Copy Trading Status*\n\n"
            f"Total Traders: {total_traders}\n"
            f"Active Subscriptions: {len(active_subs)}\n\n"
        )

        if active_subs:
            message += "*Active Copy Trading:*\n"
            for source_wallet, traders in active_subs.items():
                short_addr = f"{source_wallet[:10]}...{source_wallet[-8:]}"
                message += f"• {short_addr} → {', '.join(traders)}\n"
        else:
            message += "_No active copy trading operations_"

        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=get_trading_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Error getting trading status: {e}")
        await query.edit_message_text(
            f"❌ Error: {str(e)}",
            reply_markup=get_trading_menu_keyboard()
        )


async def start_copy_trading_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Prompt user to start copy trading.

    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    await query.answer()

    # TODO: Implement interactive flow for starting copy trading
    await query.edit_message_text(
        "▶️ *Start Copy Trading*\n\n"
        "This feature is under development.\n"
        "Use the API endpoint `/trading/copy/start` for now.",
        parse_mode="Markdown",
        reply_markup=get_trading_menu_keyboard()
    )


async def stop_copy_trading_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Prompt user to stop copy trading.

    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    await query.answer()

    # TODO: Implement interactive flow for stopping copy trading
    await query.edit_message_text(
        "⏸️ *Stop Copy Trading*\n\n"
        "This feature is under development.\n"
        "Use the API endpoint `/trading/copy/stop` for now.",
        parse_mode="Markdown",
        reply_markup=get_trading_menu_keyboard()
    )
