"""
Wallet management handlers for Telegram bot.

Handles wallet-related commands:
- /wallet: Display detailed wallet information
- /fund: Display funding instructions with QR code
- /profile: Link to Polymarket public profile
"""

import logging
import qrcode
from io import BytesIO
from telegram import Update
from telegram.ext import ContextTypes

from poly_boost.services.user_wallet_service import UserWalletService

logger = logging.getLogger(__name__)


async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /wallet command - display detailed wallet information.

    Shows wallet address, USDC balance, portfolio value, and position count.

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

        # Get wallet services
        wallet_service = context.bot_data.get('wallet_service')
        position_service = context.bot_data.get('position_service')

        balance = 0.0
        portfolio_value = 0.0
        total_positions = 0

        try:
            if wallet_service:
                balance = float(wallet_service.get_balance(wallet_obj))
            if position_service:
                summary = position_service.get_position_summary(wallet_obj)
                portfolio_value = summary.get('total_value', 0.0)
                total_positions = summary.get('total_positions', 0)
        except Exception as e:
            logger.error(f"Error fetching wallet data: {e}")

        await update.message.reply_text(
            f"💼 *Wallet Details*\n\n"
            f"Address: `{user_wallet.wallet_address}`\n"
            f"Balance: ${balance:.2f} USDC\n"
            f"Portfolio Value: ${portfolio_value:.2f}\n"
            f"Total Positions: {total_positions}\n\n"
            f"Use /positions to view positions.\n"
            f"Use /fund to add funds.",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in wallet_command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred. Please try again later."
        )


async def fund_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /fund command - display funding instructions.

    Shows wallet address for deposits with QR code and instructions.

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

        wallet_address = user_wallet.wallet_address

        # Generate QR code for address
        qr = qrcode.make(wallet_address)
        buffer = BytesIO()
        qr.save(buffer, format='PNG')
        buffer.seek(0)

        # Send QR code with caption
        await update.message.reply_photo(
            photo=buffer,
            caption=f"💰 *Fund Your Wallet*\n\n"
                    f"Send USDC (Polygon network) to:\n"
                    f"`{wallet_address}`\n\n"
                    f"⚠️ *Important:*\n"
                    f"• Use USDC on Polygon network ONLY\n"
                    f"• Double-check address before sending\n"
                    f"• Funds sent to wrong network may be lost\n\n"
                    f"Balance updates may take 1-2 minutes.",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in fund_command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred generating QR code. Please try again later."
        )


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /profile command - link to Polymarket public profile.

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

        wallet_address = user_wallet.wallet_address
        profile_url = f"https://polymarket.com/profile/{wallet_address}"

        await update.message.reply_text(
            f"📊 *Your Polymarket Profile*\n\n"
            f"View your public profile:\n"
            f"{profile_url}",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in profile_command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred. Please try again later."
        )
