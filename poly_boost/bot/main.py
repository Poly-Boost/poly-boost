"""
Telegram Bot application entry point.

Run with: python -m bot.main
"""

import logging
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from py_clob_client.client import ClobClient

from poly_boost.core.config_loader import load_config
from poly_boost.core.in_memory_activity_queue import InMemoryActivityQueue
from poly_boost.services.position_service import PositionService
from poly_boost.services.trading_service import TradingService
from poly_boost.services.wallet_service import WalletService
from poly_boost.bot.keyboards import get_main_menu_keyboard
from poly_boost.bot.handlers.position_handler import (
    show_positions_menu,
    view_all_positions,
    view_position_value
)
from poly_boost.bot.handlers.trading_handler import (
    show_trading_menu,
    view_trading_status,
    start_copy_trading_prompt,
    stop_copy_trading_prompt
)


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command.

    Args:
        update: Telegram update
        context: Bot context
    """
    await update.message.reply_text(
        "👋 *Welcome to Polymarket Copy Trading Bot!*\n\n"
        "I can help you:\n"
        "• View your positions\n"
        "• Check your balance\n"
        "• Manage copy trading\n"
        "• View trading statistics\n\n"
        "Use the menu below to get started.",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /help command.

    Args:
        update: Telegram update
        context: Bot context
    """
    help_text = (
        "ℹ️ *Help*\n\n"
        "*Commands:*\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/setwallet <address> - Set your wallet address\n"
        "/status - Show bot status\n\n"
        "*Menu Options:*\n"
        "📊 Positions - View and manage your positions\n"
        "💰 Balance - Check your USDC balance\n"
        "🔄 Copy Trading - Control copy trading operations\n"
        "📈 Stats - View trading statistics\n"
        "⚙️ Settings - Configure bot settings\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def setwallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /setwallet command.

    Args:
        update: Telegram update
        context: Bot context
    """
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a wallet address.\n"
            "Usage: `/setwallet <address>`",
            parse_mode="Markdown"
        )
        return

    wallet_address = context.args[0]

    # Basic validation
    if not wallet_address.startswith("0x") or len(wallet_address) != 42:
        await update.message.reply_text(
            "❌ Invalid wallet address format. "
            "Address should start with '0x' and be 42 characters long."
        )
        return

    # Store wallet address in user data
    context.user_data['wallet_address'] = wallet_address

    await update.message.reply_text(
        f"✅ Wallet address set to:\n`{wallet_address}`",
        parse_mode="Markdown"
    )


async def handle_menu_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle menu button presses.

    Args:
        update: Telegram update
        context: Bot context
    """
    text = update.message.text

    if text == "📊 Positions":
        await show_positions_menu(update, context)
    elif text == "💰 Balance":
        # TODO: Implement balance handler
        await update.message.reply_text("Balance feature coming soon!")
    elif text == "🔄 Copy Trading":
        await show_trading_menu(update, context)
    elif text == "📈 Stats":
        # TODO: Implement stats handler
        await update.message.reply_text("Stats feature coming soon!")
    elif text == "⚙️ Settings":
        # TODO: Implement settings handler
        await update.message.reply_text("Settings feature coming soon!")
    elif text == "ℹ️ Help":
        await help_command(update, context)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle callback queries from inline keyboards.

    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    data = query.data

    # Position handlers
    if data == "pos_view_all":
        await view_all_positions(update, context)
    elif data == "pos_value":
        await view_position_value(update, context)

    # Trading handlers
    elif data == "trade_status":
        await view_trading_status(update, context)
    elif data == "trade_start":
        await start_copy_trading_prompt(update, context)
    elif data == "trade_stop":
        await stop_copy_trading_prompt(update, context)

    # Navigation
    elif data == "back_main":
        await query.answer()
        await query.edit_message_text(
            "Main menu:",
            reply_markup=get_main_menu_keyboard()
        )


def main():
    """Run the Telegram bot."""
    try:
        # Load configuration
        config = load_config()

        # Get Telegram bot token from environment
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

        # Initialize services
        queue_config = config.get('queue', {})
        memory_config = queue_config.get('memory', {})
        max_workers = memory_config.get('max_workers', 10)
        activity_queue = InMemoryActivityQueue(max_workers=max_workers)

        # Create CLOB client
        clob_client = ClobClient(
            host="https://clob.polymarket.com",
            key="",
            chain_id=137
        )

        # Initialize services
        position_service = PositionService(clob_client)
        trading_service = TradingService(activity_queue)
        wallet_service = WalletService(clob_client)

        # Create application
        application = Application.builder().token(bot_token).build()

        # Store services in bot_data
        application.bot_data['position_service'] = position_service
        application.bot_data['trading_service'] = trading_service
        application.bot_data['wallet_service'] = wallet_service
        application.bot_data['config'] = config

        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("setwallet", setwallet_command))
        application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                handle_menu_message
            )
        )
        application.add_handler(CallbackQueryHandler(handle_callback_query))

        # Start bot
        logger.info("Starting Telegram bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
