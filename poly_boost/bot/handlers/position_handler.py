"""
Position management handlers for Telegram bot.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from poly_boost.bot.keyboards import get_position_menu_keyboard


logger = logging.getLogger(__name__)


async def show_positions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show positions management menu.

    Args:
        update: Telegram update
        context: Bot context
    """
    await update.message.reply_text(
        "📊 *Position Management*\n\n"
        "Select an option:",
        parse_mode="Markdown",
        reply_markup=get_position_menu_keyboard()
    )


async def view_all_positions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    View all positions for the user's wallet.

    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    await query.answer()

    try:
        position_service = context.bot_data['position_service']
        wallet_address = context.user_data.get('wallet_address')

        if not wallet_address:
            await query.edit_message_text(
                "❌ No wallet address configured. Use /setwallet to configure."
            )
            return

        summary = position_service.get_position_summary(wallet_address)
        total_positions = summary['total_positions']
        total_value = summary['total_value']

        message = (
            f"📊 *Your Positions*\n\n"
            f"Wallet: `{wallet_address[:10]}...{wallet_address[-8:]}`\n"
            f"Total Positions: {total_positions}\n"
            f"Total Value: ${total_value:.2f} USDC\n\n"
        )

        if total_positions == 0:
            message += "No active positions."
        else:
            message += "Position details:\n"
            # TODO: Format position details
            message += "_Position details will be displayed here_"

        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=get_position_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Error viewing positions: {e}")
        await query.edit_message_text(
            f"❌ Error: {str(e)}",
            reply_markup=get_position_menu_keyboard()
        )


async def view_position_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    View total position value.

    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    await query.answer()

    try:
        position_service = context.bot_data['position_service']
        wallet_address = context.user_data.get('wallet_address')

        if not wallet_address:
            await query.edit_message_text(
                "❌ No wallet address configured. Use /setwallet to configure."
            )
            return

        value = position_service.get_position_value(wallet_address)

        message = (
            f"💰 *Total Position Value*\n\n"
            f"Wallet: `{wallet_address[:10]}...{wallet_address[-8:]}`\n"
            f"Total Value: ${float(value):.2f} USDC"
        )

        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=get_position_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Error getting position value: {e}")
        await query.edit_message_text(
            f"❌ Error: {str(e)}",
            reply_markup=get_position_menu_keyboard()
        )
