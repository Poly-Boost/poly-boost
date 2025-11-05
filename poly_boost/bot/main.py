"""
Telegram Bot application entry point.

Run with: python -m poly_boost.bot.main
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

from polymarket_apis.clients.data_client import PolymarketDataClient
from playhouse.postgres_ext import PostgresqlExtDatabase

from poly_boost.core.config_loader import load_config
from poly_boost.core.client_factory import ClientFactory
from poly_boost.core.models import db
from poly_boost.models.user_wallet import UserWallet
from poly_boost.services.user_wallet_service import UserWalletService
from poly_boost.services.position_service import PositionService
from poly_boost.services.activity_service import ActivityService
from poly_boost.services.wallet_service import WalletService
from poly_boost.bot.conversations.wallet_init import create_wallet_init_conversation
from poly_boost.bot.handlers.wallet_handler import (
    wallet_command,
    fund_command,
    profile_command
)
from poly_boost.bot.handlers.position_handler import (
    positions_command,
    position_page_callback,
    position_select_callback,
    position_redeem_callback,
    position_list_callback
)
from poly_boost.bot.handlers.order_handler import (
    orders_command,
    order_page_callback,
    order_select_callback,
    order_cancel_callback,
    order_list_callback
)
from poly_boost.bot.handlers.activity_handler import (
    activities_command,
    activity_page_callback
)


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def initialize_database():
    """
    Initialize database connection and create tables.

    Returns:
        Database instance
    """
    # Get database configuration from environment
    db_url = os.environ.get("DATABASE_URL")

    if db_url:
        # Parse PostgreSQL URL
        logger.info("Using PostgreSQL database")
        # Format: postgresql://user:password@host:port/database
        database = PostgresqlExtDatabase(db_url)
    else:
        # Fallback to SQLite for local development
        logger.info("Using SQLite database for development")
        from peewee import SqliteDatabase
        database = SqliteDatabase('poly_boost.db')

    # Initialize database connection
    db.initialize(database)

    # Create tables
    with db:
        db.create_tables([UserWallet], safe=True)
        logger.info("Database tables created/verified")

    return db


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /help command.

    Args:
        update: Telegram update
        context: Bot context
    """
    help_text = (
        "ℹ️ *Help*\n\n"
        "*Wallet Commands:*\n"
        "/start - Initialize your wallet\n"
        "/wallet - View wallet details\n"
        "/fund - Get funding instructions\n"
        "/profile - View Polymarket profile\n\n"
        "*Position Commands:*\n"
        "/positions - View your positions\n\n"
        "*Trading Commands:*\n"
        "/orders - View active orders\n"
        "/activities - View activity history\n\n"
        "*Other Commands:*\n"
        "/help - Show this help message\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle callback queries from inline keyboards.

    Routes callbacks to appropriate handlers based on callback_data prefix.

    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    data = query.data

    try:
        # Position handlers
        if data.startswith("pos_page_"):
            await position_page_callback(update, context)
        elif data.startswith("pos_select_"):
            await position_select_callback(update, context)
        elif data.startswith("pos_redeem_"):
            await position_redeem_callback(update, context)
        elif data == "pos_list":
            await position_list_callback(update, context)

        # Order handlers
        elif data.startswith("order_page_"):
            await order_page_callback(update, context)
        elif data.startswith("order_select_"):
            await order_select_callback(update, context)
        elif data.startswith("order_cancel_"):
            await order_cancel_callback(update, context)
        elif data == "order_list":
            await order_list_callback(update, context)

        # Activity handlers
        elif data.startswith("activity_page_"):
            await activity_page_callback(update, context)

        # Ignore noop callbacks (pagination page indicator)
        elif data == "noop":
            await query.answer()

        else:
            # Unknown callback
            await query.answer("Unknown action")
            logger.warning(f"Unknown callback data: {data}")

    except Exception as e:
        logger.error(f"Error handling callback query: {e}", exc_info=True)
        try:
            await query.answer("An error occurred. Please try again.")
        except Exception:
            pass


def main():
    """Run the Telegram bot."""
    try:
        # Load configuration
        config = load_config()

        # Get Telegram bot token from environment
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

        # Initialize database
        database = initialize_database()

        # Initialize Polymarket clients
        data_client = PolymarketDataClient()
        client_factory = ClientFactory()

        # Initialize services
        user_wallet_service = UserWalletService(database=database)
        position_service = PositionService(
            clob_client=None,  # Legacy client not needed
            data_client=data_client
        )
        activity_service = ActivityService(
            data_client=data_client
        )
        wallet_service = WalletService(
            clob_client=None,  # Legacy client not needed
            client_factory=client_factory
        )

        # Create application
        application = Application.builder().token(bot_token).build()

        # Store services in bot_data
        application.bot_data['user_wallet_service'] = user_wallet_service
        application.bot_data['position_service'] = position_service
        application.bot_data['activity_service'] = activity_service
        application.bot_data['wallet_service'] = wallet_service
        application.bot_data['client_factory'] = client_factory
        application.bot_data['config'] = config

        # Add conversation handlers (must be added first for priority)
        wallet_init_conversation = create_wallet_init_conversation()
        application.add_handler(wallet_init_conversation)

        # Add command handlers
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("wallet", wallet_command))
        application.add_handler(CommandHandler("fund", fund_command))
        application.add_handler(CommandHandler("profile", profile_command))
        application.add_handler(CommandHandler("positions", positions_command))
        application.add_handler(CommandHandler("orders", orders_command))
        application.add_handler(CommandHandler("activities", activities_command))

        # Add callback query handler (for all inline keyboard buttons)
        application.add_handler(CallbackQueryHandler(handle_callback_query))

        # Start bot
        logger.info("Starting Telegram bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
