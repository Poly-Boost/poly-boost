"""
Wallet initialization conversation handler for Telegram bot.

Handles multi-step wallet setup flow:
1. User chooses to generate new wallet or import existing
2. If generate: Create new EOA wallet and store in database
3. If import: Prompt for private key, validate, and store

Per FR-004: Private key messages are deleted immediately after processing.
"""

import logging
from eth_account import Account
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from poly_boost.services.user_wallet_service import UserWalletService

logger = logging.getLogger(__name__)

# Conversation states
WALLET_CHOICE = 0
INPUT_PRIVATE_KEY = 1


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
    """
    user_id = update.effective_user.id
    user_wallet_service: UserWalletService = context.bot_data.get('user_wallet_service')

    if not user_wallet_service:
        await update.message.reply_text(
            "Service temporarily unavailable. Please try again later."
        )
        return ConversationHandler.END

    try:
        # Check if wallet exists
        if user_wallet_service.wallet_exists(user_id):
            user_wallet = user_wallet_service.get_user_wallet(user_id)
            wallet_obj = user_wallet.to_wallet()

            # Get balance and portfolio value
            wallet_service = context.bot_data.get('wallet_service')
            position_service = context.bot_data.get('position_service')

            balance = 0.0
            portfolio_value = 0.0

            try:
                if wallet_service:
                    balance = float(wallet_service.get_balance(wallet_obj))
                if position_service:
                    portfolio_value = float(position_service.get_position_value(wallet_obj))
            except Exception as e:
                logger.error(f"Error fetching wallet data: {e}")

            await update.message.reply_text(
                f"👛 *Your Wallet*\n\n"
                f"Address: `{user_wallet.wallet_address}`\n"
                f"Balance: ${balance:.2f} USDC\n"
                f"Portfolio Value: ${portfolio_value:.2f}\n\n"
                f"Use /wallet for details or /fund to add funds.",
                parse_mode="Markdown"
            )
            return ConversationHandler.END

        # Start wallet initialization flow
        keyboard = [
            [InlineKeyboardButton("🆕 Generate New Wallet", callback_data="wallet_generate")],
            [InlineKeyboardButton("📥 Import Existing Wallet", callback_data="wallet_import")]
        ]

        await update.message.reply_text(
            "Welcome to Polymarket Bot! 🎉\n\n"
            "Please set up your wallet to get started:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return WALLET_CHOICE

    except Exception as e:
        logger.error(f"Error in start_command: {e}", exc_info=True)
        await update.message.reply_text(
            "An error occurred. Please try again later."
        )
        return ConversationHandler.END


async def wallet_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle wallet generation or import choice.

    Callback data: "wallet_generate" or "wallet_import"

    Args:
        update: Telegram callback query with choice.
        context: Bot context.

    Returns:
        ConversationHandler state (INPUT_PRIVATE_KEY or END).
    """
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_wallet_service: UserWalletService = context.bot_data.get('user_wallet_service')

    if not user_wallet_service:
        await query.edit_message_text(
            "Service temporarily unavailable. Please try again later."
        )
        return ConversationHandler.END

    try:
        if query.data == "wallet_generate":
            # Generate new EOA wallet
            account = Account.create()
            wallet_address = account.address
            private_key = account.key.hex()

            # Store in database
            user_wallet_service.create_user_wallet(
                telegram_user_id=user_id,
                wallet_address=wallet_address,
                private_key=private_key,
                wallet_name=f"Wallet_{user_id}"
            )

            logger.info(f"Created new wallet for user {user_id}: {wallet_address}")

            await query.edit_message_text(
                f"✅ *Wallet Created*\n\n"
                f"Address: `{wallet_address}`\n\n"
                f"⚠️ *SAVE YOUR PRIVATE KEY:*\n"
                f"`{private_key}`\n\n"
                f"Keep this key safe! If lost, you cannot recover your wallet.\n\n"
                f"Use /wallet to view your wallet details.",
                parse_mode="Markdown"
            )

            return ConversationHandler.END

        elif query.data == "wallet_import":
            await query.edit_message_text(
                "📥 *Import Wallet*\n\n"
                "Please send your private key.\n\n"
                "Format: 0x followed by 64 hex characters\n\n"
                "⚠️ Your message will be deleted after processing for security.",
                parse_mode="Markdown"
            )
            return INPUT_PRIVATE_KEY

    except Exception as e:
        logger.error(f"Error in wallet_choice_callback: {e}", exc_info=True)
        await query.edit_message_text(
            f"❌ Error: {str(e)}\n\n"
            f"Please try again with /start."
        )
        return ConversationHandler.END


async def receive_private_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle private key input for wallet import.

    Args:
        update: Telegram message with private key.
        context: Bot context.

    Returns:
        ConversationHandler state (INPUT_PRIVATE_KEY for retry, END for success).
    """
    user_id = update.effective_user.id
    private_key = update.message.text.strip()
    user_wallet_service: UserWalletService = context.bot_data.get('user_wallet_service')

    if not user_wallet_service:
        await update.message.reply_text(
            "Service temporarily unavailable. Please try again later."
        )
        return ConversationHandler.END

    try:
        # Validate private key and derive address
        account = Account.from_key(private_key)
        wallet_address = account.address

        # Store in database
        user_wallet_service.create_user_wallet(
            telegram_user_id=user_id,
            wallet_address=wallet_address,
            private_key=private_key,
            wallet_name=f"Wallet_{user_id}"
        )

        logger.info(f"Imported wallet for user {user_id}: {wallet_address}")

        # Delete message containing private key (FR-004)
        try:
            await update.message.delete()
        except Exception as e:
            logger.warning(f"Failed to delete private key message: {e}")

        # Send success message
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ *Wallet Imported*\n\n"
                 f"Address: `{wallet_address}`\n\n"
                 f"Your wallet is ready to use.\n"
                 f"Use /wallet to view details.",
            parse_mode="Markdown"
        )

        return ConversationHandler.END

    except ValueError as e:
        logger.warning(f"Invalid private key from user {user_id}: {e}")
        await update.message.reply_text(
            "❌ *Invalid Private Key*\n\n"
            "Please check the format and try again.\n\n"
            "Format: 0x followed by 64 hex characters\n"
            "Example: 0x1234...5678...abcd\n\n"
            "Send /cancel to abort.",
            parse_mode="Markdown"
        )
        return INPUT_PRIVATE_KEY

    except Exception as e:
        logger.error(f"Error importing wallet: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Error: {str(e)}\n\n"
            f"Please try again or send /cancel to abort."
        )
        return INPUT_PRIVATE_KEY


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle /cancel command during wallet initialization.

    Args:
        update: Telegram update.
        context: Bot context.

    Returns:
        ConversationHandler.END
    """
    await update.message.reply_text(
        "Wallet setup cancelled.\n\n"
        "Use /start to try again."
    )
    return ConversationHandler.END


# ConversationHandler configuration
def create_wallet_init_conversation() -> ConversationHandler:
    """
    Create and configure the wallet initialization conversation handler.

    Returns:
        ConversationHandler for wallet initialization.
    """
    return ConversationHandler(
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
