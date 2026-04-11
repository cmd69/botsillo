"""Teclados inline para flujo Portfolio (inversiones)."""
from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Letra: c=consultar, e=compra, i=venta, m=movimiento capital EUR
_MODE_LETTER = {"consult": "c", "expense": "e", "income": "i", "movement": "m"}


def portfolio_wallets_kb(wallets: list[dict], mode: str) -> InlineKeyboardMarkup:
    """Una fila por billetera. mode: consult | expense | income | movement."""
    letter = _MODE_LETTER.get(mode, "c")
    rows: list[list[InlineKeyboardButton]] = []
    for w in wallets:
        wid = str(w["id"])
        name = (w.get("name") or "Sin nombre")[:40]
        rows.append([
            InlineKeyboardButton(
                text=f"🏦 {name}",
                callback_data=f"pw:{letter}:{wid}",
            ),
        ])
    rows.append([InlineKeyboardButton(text="Atrás", callback_data="pf:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def portfolio_consult_ficha_kb(wallet_id: UUID) -> InlineKeyboardMarkup:
    wid = str(wallet_id)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Ver detalle completo", callback_data=f"pfd:{wid}")],
        [InlineKeyboardButton(text="🔄 Otra billetera", callback_data="pf:pw_back")],
        [InlineKeyboardButton(text="Atrás (Portfolio)", callback_data="pf:menu")],
    ])


def portfolio_move_ficha_kb() -> InlineKeyboardMarkup:
    """Tras elegir billetera para movimiento de capital (EUR)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Continuar", callback_data="pf:mov_go")],
        [InlineKeyboardButton(text="🔄 Otra billetera", callback_data="pf:pw_back")],
        [InlineKeyboardButton(text="Atrás (Portfolio)", callback_data="pf:menu")],
    ])


def portfolio_op_ficha_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Continuar", callback_data="pf:op_assets")],
        [InlineKeyboardButton(text="🔄 Otra billetera", callback_data="pf:pw_back")],
        [InlineKeyboardButton(text="Atrás (Portfolio)", callback_data="pf:menu")],
    ])


def portfolio_bank_accounts_kb(accounts: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for acc in accounts:
        aid = str(acc["id"])
        label = (acc.get("name") or "Cuenta")[:32]
        rows.append([
            InlineKeyboardButton(text=f"🏦 {label}", callback_data=f"pb:{aid}"),
        ])
    rows.append([
        InlineKeyboardButton(text="Atrás", callback_data="pf:mov_back_ficha"),
        InlineKeyboardButton(text="Cancelar", callback_data="pf:cancel"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def portfolio_mov_dir_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Aporte (EUR)", callback_data="pf:mov_dep"),
            InlineKeyboardButton(text="Retirada (EUR)", callback_data="pf:mov_wd"),
        ],
        [
            InlineKeyboardButton(text="Atrás", callback_data="pf:mov_back_bank"),
            InlineKeyboardButton(text="Cancelar", callback_data="pf:cancel"),
        ],
    ])


def portfolio_assets_kb(assets: list[dict]) -> InlineKeyboardMarkup:
    """Lista activos excluyendo USDT (el backend gestiona USDT automaticamente)."""
    rows: list[list[InlineKeyboardButton]] = []
    for a in assets:
        if (a.get("symbol") or "").upper() == "USDT":
            continue
        aid = str(a["id"])
        sym = (a.get("symbol") or "?")[:12]
        name = (a.get("name") or "")[:28]
        label = f"{sym} — {name}".strip(" —")
        rows.append([
            InlineKeyboardButton(text=label[:64], callback_data=f"pa:{aid}"),
        ])
    rows.append([
        InlineKeyboardButton(text="↩️ Atras", callback_data="pf:op_back_ficha"),
        InlineKeyboardButton(text="❌ Cancelar", callback_data="pf:cancel"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
