from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app import texts


def back_cancel_row() -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data="back"),
        InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="cancel"),
    ]


def cancel_button() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="cancel")]


def confirm_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=texts.BTN_CONFIRM, callback_data="confirm"),
            InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="cancel"),
        ],
    ])


def skip_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=texts.BTN_SKIP, callback_data="skip"),
            InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="cancel"),
        ],
    ])
