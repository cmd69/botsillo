from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def cancel_row() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel")]


def back_cancel_row() -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(text="↩️ Atras", callback_data="back"),
        InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel"),
    ]


def confirm_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirmar", callback_data="confirm"),
            InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel"),
        ],
    ])


def empty_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📭 Vacio", callback_data="skip")],
        [
            InlineKeyboardButton(text="↩️ Atras", callback_data="back"),
            InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel"),
        ],
    ])


def back_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Atras", callback_data="main_menu")],
    ])
