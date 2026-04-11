"""Portfolio: consultar billeteras y registrar operaciones buy/sell (API Expensivo)."""
from __future__ import annotations

import html
from datetime import date
from decimal import Decimal
from uuid import UUID

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.api_client import (
    create_asset_operation,
    create_capital_contribution,
    get_wallet_summary,
    list_bank_accounts,
    list_investment_wallets,
    list_wallet_assets,
)
from app.db import User
from app.formatting import (
    fmt_crypto_qty,
    fmt_date_ddmmyyyy,
    fmt_fiat_or_usdt_2dp,
    parse_non_negative_decimal,
    parse_positive_decimal,
)
from app.keyboards.common import confirm_cancel_kb, empty_cancel_kb
from app.keyboards.date_picker import day_step_kb, month_step_kb
from app.keyboards.portfolio import (
    portfolio_assets_kb,
    portfolio_bank_accounts_kb,
    portfolio_mov_dir_kb,
    portfolio_tx_inline_kb,
    portfolio_wallet_hub_kb,
    portfolio_wallets_grid_kb,
)
from app.states import PortfolioFlow

router = Router(name="portfolio")

PF_DATE_PREFIX = "pfm"
PFC_DATE_PREFIX = "pfc"

_MAX_MSG = 3900


def _portfolio_done_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Atrás", callback_data="pf:pw_list")],
    ])


def _usdt_qty(assets: list[dict]) -> Decimal:
    for a in assets:
        if (a.get("symbol") or "").upper() == "USDT":
            try:
                return Decimal(str(a.get("quantity", 0)))
            except Exception:
                return Decimal(0)
    return Decimal(0)


def _summary_ficha_text(name: str, summary: dict) -> str:
    safe_name = html.escape(name or "", quote=False)
    assets = summary.get("assets") or []
    usdt = _usdt_qty(assets)
    lines = [
        f"🏦 <b>{safe_name}</b>\n",
        f"💶 Aportado: <b>{fmt_fiat_or_usdt_2dp(summary.get('total_contributed'))}</b> €",
        f"📊 Invertido: <b>{fmt_fiat_or_usdt_2dp(summary.get('total_invested'))}</b>",
        f"💹 Valor actual: <b>{fmt_fiat_or_usdt_2dp(summary.get('current_value'))}</b>",
        f"📈 P/L: <b>{fmt_fiat_or_usdt_2dp(summary.get('profit_loss'))}</b>",
        f"📉 ROI: <b>{fmt_fiat_or_usdt_2dp(summary.get('roi_percentage'))}</b> %",
        f"\n💵 <b>USDT disponible:</b> {fmt_fiat_or_usdt_2dp(usdt)}",
    ]
    return "\n".join(lines)


def _fmt_unit_price(val: object) -> str:
    """Precio por unidad (USDT): hasta 6 decimales, sin ceros finales innecesarios."""
    if val is None:
        return "-"
    try:
        d = Decimal(str(val))
    except Exception:
        return str(val)
    q = d.quantize(Decimal("0.000001"))
    s = format(q, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def _wallet_detail_html(summary: dict) -> str:
    """
    Detalle en HTML (Telegram): cabecera = mismo resumen que el hub; activos con
    cantidad, PM, precio actual, valor y coste (API WalletSummary / AssetHoldings).
    """
    name = summary.get("wallet_name") or "Billetera"
    parts: list[str] = [
        _summary_ficha_text(name, summary),
        "",
        "<i>╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌</i>",
        "",
        "<b>📊 Posiciones</b>",
        "<i>Importes según precios actuales y operaciones en Expensivo.</i>",
        "",
    ]

    raw_assets = list(summary.get("assets") or [])

    def _qty(h: dict) -> Decimal:
        try:
            return Decimal(str(h.get("quantity", 0)))
        except Exception:
            return Decimal(0)

    holdings = [h for h in raw_assets if _qty(h) != 0]
    holdings.sort(
        key=lambda h: abs(float(h.get("current_value") or h.get("total_cost") or 0)),
        reverse=True,
    )

    if not holdings:
        parts.append("<i>Sin posiciones con saldo.</i>")
    else:
        shown = holdings[:25]
        for idx, h in enumerate(shown):
            sym = html.escape(str(h.get("symbol") or "?"), quote=False)
            aname = html.escape(str(h.get("name") or ""), quote=False)
            title = f"<b>{sym}</b>"
            if aname:
                title += f" · <i>{aname}</i>"
            pl = h.get("profit_loss")
            pl_pct = h.get("profit_loss_percentage")
            pl_prefix = ""
            try:
                if pl is not None and Decimal(str(pl)) > 0:
                    pl_prefix = "+"
            except Exception:
                pass
            pl_s = f"{pl_prefix}{fmt_fiat_or_usdt_2dp(pl)}" if pl is not None else "-"
            pct_s = ""
            if pl_pct is not None:
                try:
                    p = Decimal(str(pl_pct))
                    pp = "+" if p > 0 else ""
                    pct_s = f" ({pp}{fmt_fiat_or_usdt_2dp(p)}%)"
                except Exception:
                    pct_s = ""

            parts.append(f"▸ {title}")
            parts.append(
                f"   <b>Cantidad</b> <code>{fmt_crypto_qty(h.get('quantity'))}</code>"
                f" · <b>P. medio</b> <code>{_fmt_unit_price(h.get('average_price'))}</code>"
                f" · <b>P. actual</b> <code>{_fmt_unit_price(h.get('current_price'))}</code>"
            )
            parts.append(
                f"   <b>Valor</b> {fmt_fiat_or_usdt_2dp(h.get('current_value'))} USDT"
                f" · <b>Coste</b> {fmt_fiat_or_usdt_2dp(h.get('total_cost'))} USDT"
            )
            parts.append(f"   <b>P/L</b> {pl_s} USDT{pct_s}")
            if idx < len(shown) - 1:
                parts.append("")
        if len(holdings) > 25:
            parts.append("")
            parts.append(f"<i>… y {len(holdings) - 25} mas en Expensivo</i>")

    text = "\n".join(parts)
    if len(text) > _MAX_MSG:
        text = text[: _MAX_MSG - 50] + "\n\n<i>… mensaje truncado</i>"
    return text


def _op_kind_label(op_api_type: str) -> str:
    return "Compra (gasto USDT)" if op_api_type == "buy" else "Venta (ingreso USDT)"


def _tx_success_message(result: dict, data: dict) -> str:
    wname = data.get("wallet_name") or "—"
    sym = (data.get("asset_symbol") or "?").upper()
    aname = (data.get("asset_name") or "").strip()
    act_line = f"📌 <b>Activo:</b> {sym}"
    if aname:
        act_line += f" — {aname}"

    op_type = str(result.get("type", data.get("op_api_type", "buy")))
    raw_d = result.get("date") or data.get("op_date")
    try:
        d_fmt = fmt_date_ddmmyyyy(str(raw_d)[:10])
    except (ValueError, TypeError):
        d_fmt = str(raw_d)

    notes = result.get("notes") or data.get("op_notes") or ""
    notes_line = f"\n📝 <b>Notas:</b> {notes}" if str(notes).strip() else ""

    ae = result.get("amount_eur")
    ae_line = ""
    if ae is not None:
        ae_line = f"\n💶 <b>Equiv. EUR:</b> {fmt_fiat_or_usdt_2dp(ae)} €"

    return (
        "✅ <b>Transaccion registrada</b>\n\n"
        f"🏦 <b>Billetera:</b> {wname}\n"
        f"{act_line}\n"
        f"📊 <b>Tipo:</b> {_op_kind_label(op_type)}\n"
        f"🔢 <b>Cantidad:</b> {fmt_crypto_qty(result.get('quantity'))}\n"
        f"💵 <b>Precio/u (USDT):</b> {fmt_fiat_or_usdt_2dp(result.get('price_per_unit'))}\n"
        f"💰 <b>Total (USDT):</b> {fmt_fiat_or_usdt_2dp(result.get('total_amount'))}\n"
        f"📎 <b>Comisiones:</b> {fmt_fiat_or_usdt_2dp(result.get('fees'))}\n"
        f"📅 <b>Fecha:</b> {d_fmt}"
        f"{ae_line}"
        f"{notes_line}"
    )


def _mov_success_message(result: dict, data: dict) -> str:
    wname = data.get("wallet_name") or "—"
    bname = data.get("mov_bank_name") or "—"
    sign = int(data.get("mov_sign", 1))
    label = "Aporte a la billetera" if sign > 0 else "Retirada de la billetera"

    raw_d = result.get("date") or data.get("mov_date")
    try:
        d_fmt = fmt_date_ddmmyyyy(str(raw_d)[:10])
    except (ValueError, TypeError):
        d_fmt = str(raw_d)

    amt = result.get("amount", data.get("mov_amount_eur"))
    desc = result.get("description") or data.get("mov_description") or ""
    desc_line = f"\n📝 <b>Descripcion:</b> {desc}" if str(desc).strip() else ""

    ausd = result.get("amount_usd")
    usd_line = ""
    if ausd is not None:
        usd_line = f"\n💵 <b>Equiv. USD:</b> {fmt_fiat_or_usdt_2dp(ausd)}"

    return (
        "✅ <b>Movimiento registrado</b>\n\n"
        f"🏦 <b>Billetera:</b> {wname}\n"
        f"🏛 <b>Cuenta bancaria:</b> {bname}\n"
        f"💶 <b>Tipo:</b> {label}\n"
        f"💰 <b>Importe:</b> {fmt_fiat_or_usdt_2dp(amt)} EUR\n"
        f"📅 <b>Fecha:</b> {d_fmt}"
        f"{usd_line}"
        f"{desc_line}"
    )


async def _pf_show_assets_pick(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    data = await state.get_data()
    wid_raw = data.get("wallet_id")
    if not wid_raw:
        await callback.answer()
        return
    try:
        wallet_id = UUID(str(wid_raw))
    except ValueError:
        await callback.answer()
        return

    assets = await list_wallet_assets(user.id, wallet_id)
    tradable = [a for a in assets if (a.get("symbol") or "").upper() != "USDT"]
    if not tradable:
        await callback.answer(
            "No hay activos operables (solo USDT). Crealos en Expensivo.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "Selecciona el <b>activo</b> para la operacion:",
        reply_markup=portfolio_assets_kb(assets),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.op_asset)
    await callback.answer()


async def _show_portfolio_wallet_grid(message: Message, state: FSMContext, user: User) -> None:
    wallets = await list_investment_wallets(user.id)
    await state.update_data(user_id=str(user.id))
    if not wallets:
        await message.edit_text(
            "No tienes billeteras de inversion. Crealas en Expensivo.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Atrás", callback_data="main_menu")],
            ]),
        )
        await state.clear()
        await state.update_data(user_id=str(user.id))
        return
    await message.edit_text(
        "<b>Portfolio</b> — elige una billetera:",
        reply_markup=portfolio_wallets_grid_kb(wallets),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.picking_wallet)


async def _pf_render_wallet_hub(message: Message, state: FSMContext, user: User) -> bool:
    data = await state.get_data()
    wid_raw = data.get("wallet_id")
    if not wid_raw:
        return False
    try:
        wallet_id = UUID(str(wid_raw))
    except ValueError:
        return False
    summary = await get_wallet_summary(user.id, wallet_id)
    if not summary:
        return False
    name = summary.get("wallet_name") or data.get("wallet_name") or "Billetera"
    await state.update_data(wallet_name=name)
    text = _summary_ficha_text(name, summary)
    await message.edit_text(
        text,
        reply_markup=portfolio_wallet_hub_kb(wallet_id),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.wallet_hub)
    return True


async def open_portfolio_from_menu(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    """Entrada desde menu raiz (Portfolio). Evita import circular con menu.py."""
    await state.clear()
    await state.update_data(user_id=str(user.id))
    await _show_portfolio_wallet_grid(callback.message, state, user)
    await callback.answer()


# --- Lista / hub ---


@router.callback_query(F.data == "pf:pw_list")
async def pf_pw_list(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await state.clear()
    await state.update_data(user_id=str(user.id))
    await _show_portfolio_wallet_grid(callback.message, state, user)
    await callback.answer()


@router.callback_query(F.data == "pf:hub_resume")
async def pf_hub_resume(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    ok = await _pf_render_wallet_hub(callback.message, state, user)
    if ok:
        await callback.answer()
        return
    await state.clear()
    await state.update_data(user_id=str(user.id))
    await _show_portfolio_wallet_grid(callback.message, state, user)
    await callback.answer()


@router.callback_query(F.data == "pf:cancel")
async def pf_cancel(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await state.clear()
    await state.update_data(user_id=str(user.id))
    await _show_portfolio_wallet_grid(callback.message, state, user)
    await callback.answer()


@router.callback_query(
    F.data == "pf:hub_tx",
    StateFilter(PortfolioFlow.wallet_hub, PortfolioFlow.op_asset),
)
async def pf_hub_tx(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "<b>Transaccion</b>: compra o venta de un activo.\n\nElige el tipo:",
        reply_markup=portfolio_tx_inline_kb(),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.wallet_hub)
    await callback.answer()


@router.callback_query(PortfolioFlow.wallet_hub, F.data == "pf:hub:buy")
async def pf_hub_buy(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await state.update_data(op_api_type="buy")
    await _pf_show_assets_pick(callback, state, user)


@router.callback_query(PortfolioFlow.wallet_hub, F.data == "pf:hub:sell")
async def pf_hub_sell(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await state.update_data(op_api_type="sell")
    await _pf_show_assets_pick(callback, state, user)


@router.callback_query(PortfolioFlow.wallet_hub, F.data == "pf:hub:mov")
async def pf_hub_mov(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    accounts = await list_bank_accounts(user.id)
    if not accounts:
        await callback.answer(
            "No hay cuentas bancarias. Crealas en Expensivo.",
            show_alert=True,
        )
        return
    await callback.message.edit_text(
        "<b>Movimiento de capital</b> (EUR). Selecciona la cuenta bancaria:",
        reply_markup=portfolio_bank_accounts_kb(accounts),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.mov_bank)
    await callback.answer()


# --- Elegir billetera ---


@router.callback_query(PortfolioFlow.picking_wallet, F.data.startswith("pw:"))
async def pf_pick_wallet(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    parts = callback.data.split(":", 1)
    if len(parts) != 2 or parts[0] != "pw":
        await callback.answer()
        return
    wid_raw = parts[1]
    try:
        wallet_id = UUID(wid_raw)
    except ValueError:
        await callback.answer("Billetera no valida. Abre Portfolio de nuevo.", show_alert=True)
        return

    summary = await get_wallet_summary(user.id, wallet_id)
    if not summary:
        await callback.answer("No se pudo cargar el resumen.", show_alert=True)
        return

    name = summary.get("wallet_name") or "Billetera"
    await state.update_data(wallet_id=wid_raw, wallet_name=name)
    await _pf_render_wallet_hub(callback.message, state, user)
    await callback.answer()


# --- Consultar: detalle ---


@router.callback_query(F.data.startswith("pfd:"))
async def pf_wallet_detail(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    wid_raw = callback.data.split(":", 1)[1]
    data = await state.get_data()
    if wid_raw != data.get("wallet_id"):
        await callback.answer("Billetera distinta a la seleccionada.", show_alert=True)
        return

    try:
        wallet_id = UUID(wid_raw)
    except ValueError:
        await callback.answer()
        return

    summary = await get_wallet_summary(user.id, wallet_id)
    if not summary:
        await callback.answer("No se pudo cargar el detalle.", show_alert=True)
        return

    text = _wallet_detail_html(summary)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Atrás", callback_data="pf:hub_resume")],
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# --- Movimiento de capital (EUR) ---


@router.callback_query(PortfolioFlow.mov_bank, F.data.startswith("pb:"))
async def pf_mov_pick_bank(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    aid = callback.data.split(":", 1)[1]
    accounts = await list_bank_accounts(user.id)
    acc = next((a for a in accounts if str(a.get("id")) == aid), None)
    bank_name = (acc.get("name") if acc else None) or "Cuenta"
    await state.update_data(mov_bank_account_id=aid, mov_bank_name=bank_name)
    await callback.message.edit_text(
        "Tipo de <b>movimiento</b> en EUR:",
        reply_markup=portfolio_mov_dir_kb(),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.mov_pick_dir)
    await callback.answer()


@router.callback_query(PortfolioFlow.mov_pick_dir, F.data == "pf:mov_back_bank")
async def pf_mov_back_bank_cb(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    accounts = await list_bank_accounts(user.id)
    if not accounts:
        ok = await _pf_render_wallet_hub(callback.message, state, user)
        if not ok:
            await pf_cancel(callback, state, user)
        await callback.answer()
        return
    await callback.message.edit_text(
        "Selecciona la <b>cuenta bancaria</b> de origen:",
        reply_markup=portfolio_bank_accounts_kb(accounts),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.mov_bank)
    await callback.answer()


@router.callback_query(PortfolioFlow.mov_pick_dir, F.data == "pf:mov_dep")
async def pf_mov_dep(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(mov_sign=1)
    await callback.message.edit_text(
        "<b>Aporte</b>: importe en EUR que entra a la billetera.\nEj: 500.00",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="↩️ Atras", callback_data="pf:mov_back_dir"),
                InlineKeyboardButton(text="❌ Cancelar", callback_data="pf:cancel"),
            ],
        ]),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.mov_amount)
    await callback.answer()


@router.callback_query(PortfolioFlow.mov_pick_dir, F.data == "pf:mov_wd")
async def pf_mov_wd(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(mov_sign=-1)
    await callback.message.edit_text(
        "<b>Retirada</b>: importe en EUR que sale de la billetera.\nEj: 200.00",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="↩️ Atras", callback_data="pf:mov_back_dir"),
                InlineKeyboardButton(text="❌ Cancelar", callback_data="pf:cancel"),
            ],
        ]),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.mov_amount)
    await callback.answer()


@router.callback_query(PortfolioFlow.mov_amount, F.data == "pf:mov_back_dir")
async def pf_mov_back_dir_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "Tipo de <b>movimiento</b> en EUR:",
        reply_markup=portfolio_mov_dir_kb(),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.mov_pick_dir)
    await callback.answer()


@router.message(PortfolioFlow.mov_amount)
async def pf_mov_amount_msg(message: Message, state: FSMContext) -> None:
    raw = parse_positive_decimal(message.text or "")
    if raw is None:
        await message.answer("Formato invalido. Ej: 100 o 50.50")
        return
    data = await state.get_data()
    sign = int(data.get("mov_sign", 1))
    amt = raw * sign
    await state.update_data(mov_amount_eur=str(amt))
    await message.answer(
        "Fecha del movimiento — elige el mes:",
        reply_markup=month_step_kb(PFC_DATE_PREFIX),
    )
    await state.set_state(PortfolioFlow.mov_month)


@router.callback_query(PortfolioFlow.mov_month, F.data.startswith(f"{PFC_DATE_PREFIX}:m:"))
async def pf_mov_sel_month(callback: CallbackQuery, state: FSMContext) -> None:
    ym = callback.data.split(":", 2)[2]
    year, month = int(ym.split("-")[0]), int(ym.split("-")[1])
    await state.update_data(cal_year=year, cal_month=month)
    await callback.message.edit_text(
        "Selecciona el dia:",
        reply_markup=day_step_kb(PFC_DATE_PREFIX, year, month),
    )
    await state.set_state(PortfolioFlow.mov_day)
    await callback.answer()


@router.callback_query(PortfolioFlow.mov_month, F.data.startswith(f"{PFC_DATE_PREFIX}:y:"))
async def pf_mov_year(callback: CallbackQuery) -> None:
    year = int(callback.data.split(":", 2)[2])
    await callback.message.edit_reply_markup(reply_markup=month_step_kb(PFC_DATE_PREFIX, year))
    await callback.answer()


@router.callback_query(PortfolioFlow.mov_month, F.data.startswith(f"{PFC_DATE_PREFIX}:d:"))
async def pf_mov_quick_date(callback: CallbackQuery, state: FSMContext) -> None:
    iso_date = callback.data.split(":", 2)[2]
    await state.update_data(mov_date=iso_date)
    await callback.message.edit_text(
        "Descripcion (opcional). Enviala o pulsa Vacio.",
        reply_markup=empty_cancel_kb(),
    )
    await state.set_state(PortfolioFlow.mov_desc)
    await callback.answer()


@router.callback_query(PortfolioFlow.mov_month, F.data == "cancel")
async def pf_mov_month_cancel(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await pf_cancel(callback, state, user)


@router.callback_query(PortfolioFlow.mov_month, F.data == "back")
async def pf_mov_month_back(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    sign = int(data.get("mov_sign", 1))
    label, hint = ("Aporte", "entra") if sign > 0 else ("Retirada", "sale")
    await callback.message.edit_text(
        f"<b>{label}</b>: importe en EUR que {hint} de la billetera.\nEj: 500.00",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="↩️ Atras", callback_data="pf:mov_back_dir"),
                InlineKeyboardButton(text="❌ Cancelar", callback_data="pf:cancel"),
            ],
        ]),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.mov_amount)
    await callback.answer()


@router.callback_query(PortfolioFlow.mov_day, F.data.startswith(f"{PFC_DATE_PREFIX}:d:"))
async def pf_mov_sel_day(callback: CallbackQuery, state: FSMContext) -> None:
    iso_date = callback.data.split(":", 2)[2]
    await state.update_data(mov_date=iso_date)
    await callback.message.edit_text(
        "Descripcion (opcional). Enviala o pulsa Vacio.",
        reply_markup=empty_cancel_kb(),
    )
    await state.set_state(PortfolioFlow.mov_desc)
    await callback.answer()


@router.callback_query(PortfolioFlow.mov_day, F.data == "back")
async def pf_mov_day_back(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    year = data.get("cal_year", date.today().year)
    month = data.get("cal_month", date.today().month)
    await callback.message.edit_text(
        "Fecha — elige el mes:",
        reply_markup=month_step_kb(PFC_DATE_PREFIX, year),
    )
    await state.set_state(PortfolioFlow.mov_month)
    await callback.answer()


@router.callback_query(PortfolioFlow.mov_day, F.data == "cancel")
async def pf_mov_day_cancel(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await pf_cancel(callback, state, user)


@router.message(PortfolioFlow.mov_desc)
async def pf_mov_desc_msg(message: Message, state: FSMContext) -> None:
    await state.update_data(mov_description=message.text.strip())
    await _pf_show_mov_confirm(message, state)


@router.callback_query(PortfolioFlow.mov_desc, F.data == "skip")
async def pf_mov_desc_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(mov_description="")
    data = await state.get_data()
    await callback.message.edit_text(
        _pf_mov_confirm_text(data),
        reply_markup=confirm_cancel_kb(),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.mov_confirm)
    await callback.answer()


@router.callback_query(PortfolioFlow.mov_desc, F.data == "back")
async def pf_mov_desc_back(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "Fecha del movimiento — elige el mes:",
        reply_markup=month_step_kb(PFC_DATE_PREFIX),
    )
    await state.set_state(PortfolioFlow.mov_month)
    await callback.answer()


@router.callback_query(PortfolioFlow.mov_desc, F.data == "cancel")
async def pf_mov_desc_cancel(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await pf_cancel(callback, state, user)


def _pf_mov_confirm_text(data: dict) -> str:
    raw_amt = data.get("mov_amount_eur", "?")
    try:
        amt = fmt_fiat_or_usdt_2dp(Decimal(str(raw_amt)))
    except Exception:
        amt = str(raw_amt)
    raw_d = data.get("mov_date", "?")
    try:
        d_fmt = fmt_date_ddmmyyyy(str(raw_d))
    except (ValueError, TypeError):
        d_fmt = str(raw_d)
    desc = data.get("mov_description") or "-"
    label = "Aporte" if int(data.get("mov_sign", 1)) > 0 else "Retirada"
    return (
        f"📌 <b>Confirmar movimiento</b>\n\n"
        f"<b>Tipo:</b> {label}\n"
        f"<b>Importe:</b> {amt} EUR\n"
        f"<b>Fecha:</b> {d_fmt}\n"
        f"<b>Descripcion:</b> {desc}\n\n"
        "¿Confirmar?"
    )


async def _pf_show_mov_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await message.answer(
        _pf_mov_confirm_text(data),
        reply_markup=confirm_cancel_kb(),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.mov_confirm)


@router.callback_query(PortfolioFlow.mov_confirm, F.data == "confirm")
async def pf_mov_confirm_ok(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    data = await state.get_data()
    try:
        bank_id = UUID(str(data["mov_bank_account_id"]))
        wallet_id = UUID(str(data["wallet_id"]))
        amt = Decimal(str(data["mov_amount_eur"]))
        mov_d = date.fromisoformat(str(data["mov_date"]))
    except Exception:
        await callback.message.edit_text("Error interno (datos).", reply_markup=_portfolio_done_kb())
        await state.clear()
        await callback.answer()
        return

    desc_raw = data.get("mov_description") or ""
    desc = desc_raw if desc_raw else None

    result, err = await create_capital_contribution(
        user_id=user.id,
        bank_account_id=bank_id,
        wallet_id=wallet_id,
        amount=amt,
        contrib_date=mov_d,
        description=desc,
    )

    if result:
        await callback.message.edit_text(
            _mov_success_message(result, data),
            reply_markup=_portfolio_done_kb(),
            parse_mode="HTML",
        )
    else:
        err_txt = err or "Error desconocido"
        await callback.message.edit_text(
            f"❌ <b>No se pudo registrar</b>\n\n{err_txt[:500]}",
            reply_markup=_portfolio_done_kb(),
            parse_mode="HTML",
        )

    await state.clear()
    await callback.answer()


@router.callback_query(PortfolioFlow.mov_confirm, F.data == "cancel")
async def pf_mov_confirm_cancel(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await pf_cancel(callback, state, user)


@router.callback_query(PortfolioFlow.op_asset, F.data.startswith("pa:"))
async def pf_pick_asset(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    aid = callback.data.split(":", 1)[1]
    data = await state.get_data()
    sym, aname = "?", ""
    wid_raw = data.get("wallet_id")
    if wid_raw:
        try:
            wuuid = UUID(str(wid_raw))
            assets = await list_wallet_assets(user.id, wuuid)
            row = next((a for a in assets if str(a.get("id")) == aid), None)
            if row:
                sym = str(row.get("symbol") or "?").upper()
                aname = str(row.get("name") or "")
        except (ValueError, TypeError):
            pass
    await state.update_data(asset_id=aid, asset_symbol=sym, asset_name=aname)
    await callback.message.edit_text(
        "Cantidad (unidades del activo):\nEj: 0.0015 o 10",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="↩️ Atras", callback_data="pf:op_pick_back"),
                InlineKeyboardButton(text="❌ Cancelar", callback_data="pf:cancel"),
            ],
        ]),
    )
    await state.set_state(PortfolioFlow.op_quantity)
    await callback.answer()


# --- Cantidad, precio, total, comisiones ---


@router.message(PortfolioFlow.op_quantity)
async def pf_op_qty_msg(message: Message, state: FSMContext) -> None:
    q = parse_positive_decimal(message.text or "")
    if q is None:
        await message.answer("Formato invalido. Ej: 0.01 o 15")
        return
    await state.update_data(op_quantity=str(q))
    await message.answer(
        "Precio por unidad:\nEj: 42000.50",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="↩️ Atras", callback_data="pf:op_back_qty"),
                InlineKeyboardButton(text="❌ Cancelar", callback_data="pf:cancel_msg"),
            ],
        ]),
    )
    await state.set_state(PortfolioFlow.op_price)


@router.callback_query(
    PortfolioFlow.op_quantity,
    (F.data == "pf:op_back_qty") | (F.data == "pf:op_pick_back"),
)
async def pf_op_back_to_assets_from_qty(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await _pf_show_assets_pick(callback, state, user)


@router.message(PortfolioFlow.op_price)
async def pf_op_price_msg(message: Message, state: FSMContext) -> None:
    p = parse_positive_decimal(message.text or "")
    if p is None:
        await message.answer("Formato invalido.")
        return
    data = await state.get_data()
    q = Decimal(data.get("op_quantity", "0"))
    suggested = (q * p).quantize(Decimal("0.00000001"))
    await state.update_data(op_price_per_unit=str(p), op_total_suggested=str(suggested))
    await message.answer(
        f"Importe <b>total</b> de la operacion (USDT u otra moneda de la billetera).\n"
        f"Sugerido: <b>{fmt_fiat_or_usdt_2dp(suggested)}</b> USDT\n\n"
        "Envia el importe final o el sugerido.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="↩️ Atras", callback_data="pf:op_back_total"),
                InlineKeyboardButton(text="❌ Cancelar", callback_data="pf:cancel_msg"),
            ],
        ]),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.op_total)


@router.callback_query(PortfolioFlow.op_price, F.data == "pf:op_back_price")
async def pf_op_back_price_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "Cantidad (unidades del activo):\nEj: 0.0015 o 10",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="↩️ Atras", callback_data="pf:op_pick_back"),
                InlineKeyboardButton(text="❌ Cancelar", callback_data="pf:cancel"),
            ],
        ]),
    )
    await state.set_state(PortfolioFlow.op_quantity)
    await callback.answer()


@router.callback_query(PortfolioFlow.op_total, F.data == "pf:op_back_total")
async def pf_op_back_total_cb(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await callback.message.edit_text(
        "Precio por unidad:\nEj: 42000.50",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="↩️ Atras", callback_data="pf:op_back_price"),
                InlineKeyboardButton(text="❌ Cancelar", callback_data="pf:cancel_msg"),
            ],
        ]),
    )
    await state.set_state(PortfolioFlow.op_price)
    await callback.answer()


@router.callback_query(F.data == "pf:cancel_msg")
async def pf_cancel_msg(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await pf_cancel(callback, state, user)


@router.message(PortfolioFlow.op_total)
async def pf_op_total_msg(message: Message, state: FSMContext) -> None:
    t = parse_positive_decimal(message.text or "")
    if t is None:
        await message.answer("Formato invalido. Debe ser mayor que 0.")
        return
    await state.update_data(op_total_amount=str(t))
    await message.answer(
        "Comisiones (opcional). Envialas o pulsa Vacio para 0.",
        reply_markup=empty_cancel_kb(),
    )
    await state.set_state(PortfolioFlow.op_fees)


@router.message(PortfolioFlow.op_fees)
async def pf_op_fees_msg(message: Message, state: FSMContext) -> None:
    f = parse_non_negative_decimal(message.text or "")
    if f is None:
        await message.answer("Formato invalido. Ej: 0 o 1.25")
        return
    await state.update_data(op_fees=str(f))
    await message.answer(
        "Fecha de la operacion — elige el mes:",
        reply_markup=month_step_kb(PF_DATE_PREFIX),
    )
    await state.set_state(PortfolioFlow.op_month)


@router.callback_query(PortfolioFlow.op_fees, F.data == "skip")
async def pf_op_fees_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(op_fees="0")
    await callback.message.edit_text(
        "Fecha de la operacion — elige el mes:",
        reply_markup=month_step_kb(PF_DATE_PREFIX),
    )
    await state.set_state(PortfolioFlow.op_month)
    await callback.answer()


@router.callback_query(PortfolioFlow.op_fees, F.data == "back")
async def pf_op_fees_back(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    suggested = data.get("op_total_suggested", "?")
    await callback.message.edit_text(
        f"Importe total (sugerido {fmt_fiat_or_usdt_2dp(suggested)} USDT):\nEnvia el importe final.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="↩️ Atras", callback_data="pf:op_back_price"),
                InlineKeyboardButton(text="❌ Cancelar", callback_data="pf:cancel"),
            ],
        ]),
    )
    await state.set_state(PortfolioFlow.op_total)
    await callback.answer()


@router.callback_query(PortfolioFlow.op_fees, F.data == "cancel")
async def pf_op_fees_cancel(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await pf_cancel(callback, state, user)


# --- Fecha operacion ---


@router.callback_query(PortfolioFlow.op_month, F.data.startswith(f"{PF_DATE_PREFIX}:m:"))
async def pf_op_sel_month(callback: CallbackQuery, state: FSMContext) -> None:
    ym = callback.data.split(":", 2)[2]
    year, month = int(ym.split("-")[0]), int(ym.split("-")[1])
    await state.update_data(cal_year=year, cal_month=month)
    await callback.message.edit_text(
        "Selecciona el dia:",
        reply_markup=day_step_kb(PF_DATE_PREFIX, year, month),
    )
    await state.set_state(PortfolioFlow.op_day)
    await callback.answer()


@router.callback_query(PortfolioFlow.op_month, F.data.startswith(f"{PF_DATE_PREFIX}:y:"))
async def pf_op_year(callback: CallbackQuery) -> None:
    year = int(callback.data.split(":", 2)[2])
    await callback.message.edit_reply_markup(reply_markup=month_step_kb(PF_DATE_PREFIX, year))
    await callback.answer()


@router.callback_query(PortfolioFlow.op_month, F.data.startswith(f"{PF_DATE_PREFIX}:d:"))
async def pf_op_quick_date(callback: CallbackQuery, state: FSMContext) -> None:
    iso_date = callback.data.split(":", 2)[2]
    await state.update_data(op_date=iso_date)
    await callback.message.edit_text(
        "Notas (opcional). Envialas o pulsa Vacio.",
        reply_markup=empty_cancel_kb(),
    )
    await state.set_state(PortfolioFlow.op_notes)
    await callback.answer()


@router.callback_query(PortfolioFlow.op_month, F.data == "cancel")
async def pf_op_month_cancel(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await pf_cancel(callback, state, user)


@router.callback_query(PortfolioFlow.op_month, F.data == "back")
async def pf_op_month_back(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "Comisiones. Envialas o pulsa Vacio para 0.",
        reply_markup=empty_cancel_kb(),
    )
    await state.set_state(PortfolioFlow.op_fees)
    await callback.answer()


@router.callback_query(PortfolioFlow.op_day, F.data.startswith(f"{PF_DATE_PREFIX}:d:"))
async def pf_op_sel_day(callback: CallbackQuery, state: FSMContext) -> None:
    iso_date = callback.data.split(":", 2)[2]
    await state.update_data(op_date=iso_date)
    await callback.message.edit_text(
        "Notas (opcional). Envialas o pulsa Vacio.",
        reply_markup=empty_cancel_kb(),
    )
    await state.set_state(PortfolioFlow.op_notes)
    await callback.answer()


@router.callback_query(PortfolioFlow.op_day, F.data == "back")
async def pf_op_day_back(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    year = data.get("cal_year", date.today().year)
    month = data.get("cal_month", date.today().month)
    await callback.message.edit_text(
        "Fecha — elige el mes:",
        reply_markup=month_step_kb(PF_DATE_PREFIX, year),
    )
    await state.set_state(PortfolioFlow.op_month)
    await callback.answer()


@router.callback_query(PortfolioFlow.op_day, F.data == "cancel")
async def pf_op_day_cancel(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await pf_cancel(callback, state, user)


# --- Notas y confirmar ---


@router.message(PortfolioFlow.op_notes)
async def pf_op_notes_msg(message: Message, state: FSMContext) -> None:
    await state.update_data(op_notes=message.text.strip())
    await _pf_show_op_confirm(message, state)


@router.callback_query(PortfolioFlow.op_notes, F.data == "skip")
async def pf_op_notes_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(op_notes="")
    data = await state.get_data()
    await callback.message.edit_text(
        _pf_op_confirm_text(data),
        reply_markup=confirm_cancel_kb(),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.op_confirm)
    await callback.answer()


@router.callback_query(PortfolioFlow.op_notes, F.data == "back")
async def pf_op_notes_back(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "Fecha de la operacion — elige el mes:",
        reply_markup=month_step_kb(PF_DATE_PREFIX),
    )
    await state.set_state(PortfolioFlow.op_month)
    await callback.answer()


@router.callback_query(PortfolioFlow.op_notes, F.data == "cancel")
async def pf_op_notes_cancel(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await pf_cancel(callback, state, user)


def _pf_op_confirm_text(data: dict) -> str:
    notes = data.get("op_notes") or "-"
    op_type = data.get("op_api_type", "buy")
    sym = (data.get("asset_symbol") or "?").upper()
    aname = (data.get("asset_name") or "").strip()
    act = sym + (f" — {aname}" if aname else "")
    return (
        f"📌 <b>Confirmar operacion</b>\n\n"
        f"<b>Tipo:</b> {_op_kind_label(str(op_type))} (<code>{op_type}</code>)\n"
        f"<b>Activo:</b> {act}\n"
        f"<b>Cantidad:</b> {fmt_crypto_qty(data.get('op_quantity'))}\n"
        f"<b>Precio/u (USDT):</b> {fmt_fiat_or_usdt_2dp(data.get('op_price_per_unit'))}\n"
        f"<b>Total (USDT):</b> {fmt_fiat_or_usdt_2dp(data.get('op_total_amount'))}\n"
        f"<b>Comisiones:</b> {fmt_fiat_or_usdt_2dp(data.get('op_fees', 0))}\n"
        f"<b>Fecha:</b> {fmt_date_ddmmyyyy(data['op_date'])}\n"
        f"<b>Notas:</b> {notes}\n\n"
        "¿Confirmar?"
    )


async def _pf_show_op_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await message.answer(
        _pf_op_confirm_text(data),
        reply_markup=confirm_cancel_kb(),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.op_confirm)


@router.callback_query(PortfolioFlow.op_confirm, F.data == "confirm")
async def pf_op_confirm_ok(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    data = await state.get_data()
    try:
        asset_id = UUID(str(data["asset_id"]))
    except Exception:
        await callback.message.edit_text("Error interno (activo).", reply_markup=_portfolio_done_kb())
        await state.clear()
        await callback.answer()
        return

    op_type = str(data.get("op_api_type", "buy"))
    qty = Decimal(str(data.get("op_quantity", "0")))
    price = Decimal(str(data.get("op_price_per_unit", "0")))
    total = Decimal(str(data.get("op_total_amount", "0")))
    fees = Decimal(str(data.get("op_fees", "0")))
    op_date = date.fromisoformat(str(data["op_date"]))
    notes_raw = data.get("op_notes") or ""
    notes = notes_raw if notes_raw else None

    result, err = await create_asset_operation(
        user_id=user.id,
        asset_id=asset_id,
        op_type=op_type,
        quantity=qty,
        price_per_unit=price,
        total_amount=total,
        fees=fees,
        op_date=op_date,
        notes=notes,
    )

    if result:
        await callback.message.edit_text(
            _tx_success_message(result, data),
            reply_markup=_portfolio_done_kb(),
            parse_mode="HTML",
        )
    else:
        err_txt = err or "Error desconocido"
        await callback.message.edit_text(
            f"❌ <b>No se pudo registrar</b>\n\n{err_txt[:500]}",
            reply_markup=_portfolio_done_kb(),
            parse_mode="HTML",
        )

    await state.clear()
    await callback.answer()


@router.callback_query(PortfolioFlow.op_confirm, F.data == "cancel")
async def pf_op_confirm_cancel(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await pf_cancel(callback, state, user)
