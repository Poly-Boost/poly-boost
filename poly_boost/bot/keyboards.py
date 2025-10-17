"""
Telegram keyboard layouts.
"""

from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Get main menu keyboard.

    Returns:
        Reply keyboard markup
    """
    keyboard = [
        ["📊 Positions", "💰 Balance"],
        ["🔄 Copy Trading", "📈 Stats"],
        ["⚙️ Settings", "ℹ️ Help"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_position_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Get position management keyboard.

    Returns:
        Inline keyboard markup
    """
    keyboard = [
        [InlineKeyboardButton("View All Positions", callback_data="pos_view_all")],
        [InlineKeyboardButton("Get Position Value", callback_data="pos_value")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_trading_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Get copy trading control keyboard.

    Returns:
        Inline keyboard markup
    """
    keyboard = [
        [InlineKeyboardButton("▶️ Start Copy Trading", callback_data="trade_start")],
        [InlineKeyboardButton("⏸️ Stop Copy Trading", callback_data="trade_stop")],
        [InlineKeyboardButton("📊 View Status", callback_data="trade_status")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """
    Get confirmation keyboard.

    Args:
        action: Action to confirm

    Returns:
        Inline keyboard markup
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{action}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
