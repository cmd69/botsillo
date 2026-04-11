"""Teclados inline para flujo Portfolio (inversiones)."""
from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Texto max por boton en rejilla 2 columnas (Telegram limite ~64 bytes callback)
_WALLET_BTN_LEN = 16


def portfolio_wallets_grid_kb(wallets: list[dict]) -> InlineKeyboardMarkup:
    """Rejilla 2 columnas. callback pw:<uuid>"""
    rows: list[list[InlineKeyboardButton]] = []
    pair: list[InlineKeyboardButton] = []
    for w in wallets:
        wid = str(w["id"])
        raw = (w.get("name") or "?").strip() or "?"
        label = raw[:_WALLET_BTN_LEN] + ("…" if len(raw) > _WALLET_BTN_LEN else "")
        pair.append(
            InlineKeyboardButton(
                text=f"🏦 {label}",
                callback_data=f"pw:{wid}",
            ),
        )
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    rows.append([InlineKeyboardButton(text="↩️ Atrás", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def portfolio_wallet_hub_kb(wallet_id: UUID) -> InlineKeyboardMarkup:
    """Acciones bajo el resumen de la billetera elegida."""
    wid = str(wallet_id)
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Detalle", callback_data=f"pfd:{wid}"),
            InlineKeyboardButton(text="📊 Transaccion", callback_data="pf:hub_tx"),
        ],
        [
            InlineKeyboardButton(text="💶 Movimiento", callback_data="pf:hub:mov"),
        ],
        [InlineKeyboardButton(text="↩️ Atrás", callback_data="pf:pw_list")],
    ])


def portfolio_tx_inline_kb() -> InlineKeyboardMarkup:
    """Subpaso transaccion: compra / venta (misma fila)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📈 Compra", callback_data="pf:hub:buy"),
            InlineKeyboardButton(text="📉 Venta", callback_data="pf:hub:sell"),
        ],
        [InlineKeyboardButton(text="↩️ Atrás", callback_data="pf:hub_resume")],
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
        InlineKeyboardButton(text="↩️ Atrás", callback_data="pf:hub_resume"),
        InlineKeyboardButton(text="❌ Cancelar", callback_data="pf:cancel"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def portfolio_mov_dir_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Aporte EUR", callback_data="pf:mov_dep"),
            InlineKeyboardButton(text="➖ Retirada EUR", callback_data="pf:mov_wd"),
        ],
        [
            InlineKeyboardButton(text="↩️ Atrás", callback_data="pf:mov_back_bank"),
            InlineKeyboardButton(text="❌ Cancelar", callback_data="pf:cancel"),
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
            InlineKeyboardButton(text=f"📊 {label[:58]}", callback_data=f"pa:{aid}"),
        ])
    rows.append([
        InlineKeyboardButton(text="↩️ Atrás", callback_data="pf:hub_tx"),
        InlineKeyboardButton(text="❌ Cancelar", callback_data="pf:cancel"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
