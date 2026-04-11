"""Portfolio: consultar billeteras y registrar operaciones buy/sell (API Expensivo)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.api_client import (
    create_asset_operation,
    create_capital_contribution,
    get_wallet_details,
    get_wallet_summary,
    list_bank_accounts,
    list_investment_wallets,
    list_wallet_assets,
)
from app.db import User
from app.formatting import (
    fmt_date_ddmmyyyy,
    parse_non_negative_decimal,
    parse_positive_decimal,
)
from app.keyboards.common import confirm_cancel_kb, empty_cancel_kb
from app.keyboards.date_picker import day_step_kb, month_step_kb
from app.keyboards.main_menu import portfolio_menu_kb, portfolio_tx_submenu_kb
from app.keyboards.portfolio import (
    portfolio_assets_kb,
    portfolio_bank_accounts_kb,
    portfolio_consult_ficha_kb,
    portfolio_move_ficha_kb,
    portfolio_mov_dir_kb,
    portfolio_op_ficha_kb,
    portfolio_wallets_kb,
)
from app.states import PortfolioFlow

router = Router(name="portfolio")

PF_DATE_PREFIX = "pfm"
PFC_DATE_PREFIX = "pfc"

_MAX_MSG = 3900


def _fmt_num(val: object) -> str:
    if val is None:
        return "-"
    try:
        d = Decimal(str(val))
    except Exception:
        return str(val)
    return format(d.normalize(), "f").rstrip("0").rstrip(".") or "0"


def _usdt_qty(assets: list[dict]) -> Decimal:
    for a in assets:
        if (a.get("symbol") or "").upper() == "USDT":
            try:
                return Decimal(str(a.get("quantity", 0)))
            except Exception:
                return Decimal(0)
    return Decimal(0)


def _summary_ficha_text(name: str, summary: dict) -> str:
    assets = summary.get("assets") or []
    usdt = _usdt_qty(assets)
    lines = [
        f"🏦 <b>{name}</b>\n",
        f"💶 Aportado: <b>{_fmt_num(summary.get('total_contributed'))}</b> €",
        f"📊 Invertido: <b>{_fmt_num(summary.get('total_invested'))}</b>",
        f"💹 Valor actual: <b>{_fmt_num(summary.get('current_value'))}</b>",
        f"📈 P/L: <b>{_fmt_num(summary.get('profit_loss'))}</b>",
        f"📉 ROI: <b>{_fmt_num(summary.get('roi_percentage'))}</b> %",
        f"\n💵 <b>USDT disponible:</b> {_fmt_num(usdt)}",
    ]
    return "\n".join(lines)


def _details_full_text(d: dict) -> str:
    name = d.get("name") or "Billetera"
    parts = [f"📋 <b>{name}</b> — detalle\n"]

    assets = d.get("assets") or []
    parts.append("\n<b>Activos</b>")
    if not assets:
        parts.append("  (ninguno)")
    else:
        for a in assets[:30]:
            sym = a.get("symbol", "?")
            aname = a.get("name", "")
            price = a.get("current_price")
            parts.append(f"  • <b>{sym}</b> {aname} — precio {_fmt_num(price)}")
        if len(assets) > 30:
            parts.append(f"  … y {len(assets) - 30} mas (ver en Expensivo)")

    contribs = sorted(
        d.get("capital_contributions") or [],
        key=lambda x: str(x.get("date") or ""),
        reverse=True,
    )
    parts.append("\n<b>Aportes de capital</b> (ultimos 15)")
    if not contribs:
        parts.append("  (ninguno)")
    else:
        for c in contribs[:15]:
            amt = c.get("amount")
            cdate = c.get("date", "")
            desc = (c.get("description") or "-")[:40]
            parts.append(f"  • {cdate}  {_fmt_num(amt)} €  {desc}")
        if len(contribs) > 15:
            parts.append(f"  … y {len(contribs) - 15} mas en la web")

    text = "\n".join(parts)
    if len(text) > _MAX_MSG:
        text = text[: _MAX_MSG - 40] + "\n\n… (truncado; abre Expensivo para ver todo)"
    return text


def _op_kind_label(op_api_type: str) -> str:
    return "Compra (gasto USDT)" if op_api_type == "buy" else "Venta (ingreso USDT)"


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


async def _show_wallet_list(message: Message, state: FSMContext, user: User) -> None:
    data = await state.get_data()
    mode = data.get("pf_mode")
    if mode not in ("consult", "expense", "income", "movement"):
        await state.clear()
        await message.edit_text("Sesion caducada.", reply_markup=portfolio_menu_kb())
        return

    wallets = await list_investment_wallets(user.id)
    if not wallets:
        await message.edit_text(
            "No tienes billeteras de inversion. Crealas en Expensivo.",
            reply_markup=portfolio_menu_kb(),
        )
        await state.clear()
        return

    title = {
        "consult": "Elige la billetera a <b>consultar</b>:",
        "expense": "Elige la billetera para <b>compra</b> (transaccion):",
        "income": "Elige la billetera para <b>venta</b> (transaccion):",
        "movement": "Elige la billetera para el <b>movimiento</b> de capital (EUR):",
    }[mode]
    await message.edit_text(
        title,
        reply_markup=portfolio_wallets_kb(wallets, mode),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.picking_wallet)


# --- Entrada menu Portfolio ---


@router.callback_query(F.data == "pf:tx_menu")
async def pf_tx_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "<b>Transacción</b>: operacion de compra o venta sobre un activo de la billetera.",
        reply_markup=portfolio_tx_submenu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "pf:consult")
async def pf_start_consult(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await state.clear()
    await state.update_data(pf_mode="consult", user_id=str(user.id))
    await _show_wallet_list(callback.message, state, user)
    await callback.answer()


@router.callback_query(F.data == "pf:expense")
async def pf_start_expense(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await state.clear()
    await state.update_data(pf_mode="expense", op_api_type="buy", user_id=str(user.id))
    await _show_wallet_list(callback.message, state, user)
    await callback.answer()


@router.callback_query(F.data == "pf:income")
async def pf_start_income(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await state.clear()
    await state.update_data(pf_mode="income", op_api_type="sell", user_id=str(user.id))
    await _show_wallet_list(callback.message, state, user)
    await callback.answer()


@router.callback_query(F.data == "pf:movement")
async def pf_start_movement(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await state.clear()
    await state.update_data(pf_mode="movement", user_id=str(user.id))
    await _show_wallet_list(callback.message, state, user)
    await callback.answer()


@router.callback_query(F.data == "pf:menu")
async def pf_back_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "<b>Portfolio</b>: consultar, transacciones de activos o movimientos de capital.",
        reply_markup=portfolio_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "pf:cancel")
async def pf_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Cancelado.", reply_markup=portfolio_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "pf:pw_back")
async def pf_back_wallet_list(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    data = await state.get_data()
    if not data.get("pf_mode"):
        await pf_back_menu(callback, state)
        return
    await _show_wallet_list(callback.message, state, user)
    await callback.answer()


# --- Elegir billetera ---


@router.callback_query(PortfolioFlow.picking_wallet, F.data.startswith("pw:"))
async def pf_pick_wallet(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    parts = callback.data.split(":", 2)
    if len(parts) != 3:
        await callback.answer()
        return
    letter, wid_raw = parts[1], parts[2]
    expected = {"c": "consult", "e": "expense", "i": "income", "m": "movement"}.get(letter)
    data = await state.get_data()
    if expected != data.get("pf_mode"):
        await callback.answer("Accion no valida. Vuelve a Portfolio.", show_alert=True)
        return

    try:
        wallet_id = UUID(wid_raw)
    except ValueError:
        await callback.answer()
        return

    summary = await get_wallet_summary(user.id, wallet_id)
    if not summary:
        await callback.answer("No se pudo cargar el resumen.", show_alert=True)
        return

    name = summary.get("wallet_name") or "Billetera"
    await state.update_data(wallet_id=wid_raw, wallet_name=name)

    text = _summary_ficha_text(name, summary)

    if data["pf_mode"] == "consult":
        await callback.message.edit_text(
            text,
            reply_markup=portfolio_consult_ficha_kb(wallet_id),
            parse_mode="HTML",
        )
        await state.set_state(PortfolioFlow.consult_after_ficha)
    elif data["pf_mode"] == "movement":
        await callback.message.edit_text(
            text + "\n\n<b>Movimiento de capital</b> (EUR desde cuenta bancaria)",
            reply_markup=portfolio_move_ficha_kb(),
            parse_mode="HTML",
        )
        await state.set_state(PortfolioFlow.mov_after_ficha)
    else:
        await callback.message.edit_text(
            text + f"\n\n{_op_kind_label(data.get('op_api_type', 'buy'))}",
            reply_markup=portfolio_op_ficha_kb(),
            parse_mode="HTML",
        )
        await state.set_state(PortfolioFlow.op_after_ficha)

    await callback.answer()


# --- Consultar: detalle ---


@router.callback_query(PortfolioFlow.consult_after_ficha, F.data.startswith("pfd:"))
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

    det = await get_wallet_details(user.id, wallet_id)
    if not det:
        await callback.answer("No se pudo cargar el detalle.", show_alert=True)
        return

    text = _details_full_text(det)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Volver al resumen", callback_data=f"pw:c:{wid_raw}")],
        [InlineKeyboardButton(text="🔄 Otra billetera", callback_data="pf:pw_back")],
        [InlineKeyboardButton(text="Atras (Portfolio)", callback_data="pf:menu")],
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# --- Movimiento de capital (EUR) ---


async def _pf_reload_move_ficha(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    data = await state.get_data()
    wid_raw = data.get("wallet_id")
    if not wid_raw:
        await pf_cancel(callback, state)
        return
    try:
        wuuid = UUID(str(wid_raw))
    except ValueError:
        await pf_cancel(callback, state)
        return
    summary = await get_wallet_summary(user.id, wuuid)
    if not summary:
        await pf_cancel(callback, state)
        return
    name = summary.get("wallet_name") or "Billetera"
    text = _summary_ficha_text(name, summary) + "\n\n<b>Movimiento de capital</b> (EUR desde cuenta bancaria)"
    await callback.message.edit_text(
        text,
        reply_markup=portfolio_move_ficha_kb(),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.mov_after_ficha)


@router.callback_query(PortfolioFlow.mov_after_ficha, F.data == "pf:mov_go")
async def pf_mov_go(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    accounts = await list_bank_accounts(user.id)
    if not accounts:
        await callback.answer(
            "No hay cuentas bancarias. Crealas en Expensivo.",
            show_alert=True,
        )
        return
    await callback.message.edit_text(
        "Selecciona la <b>cuenta bancaria</b> de origen:",
        reply_markup=portfolio_bank_accounts_kb(accounts),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.mov_bank)
    await callback.answer()


@router.callback_query(PortfolioFlow.mov_bank, F.data == "pf:mov_back_ficha")
async def pf_mov_back_ficha_cb(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await _pf_reload_move_ficha(callback, state, user)
    await callback.answer()


@router.callback_query(PortfolioFlow.mov_bank, F.data.startswith("pb:"))
async def pf_mov_pick_bank(callback: CallbackQuery, state: FSMContext) -> None:
    aid = callback.data.split(":", 1)[1]
    await state.update_data(mov_bank_account_id=aid)
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
        await _pf_reload_move_ficha(callback, state, user)
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
                InlineKeyboardButton(text="Atras", callback_data="pf:mov_back_dir"),
                InlineKeyboardButton(text="Cancelar", callback_data="pf:cancel"),
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
                InlineKeyboardButton(text="Atras", callback_data="pf:mov_back_dir"),
                InlineKeyboardButton(text="Cancelar", callback_data="pf:cancel"),
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
async def pf_mov_month_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await pf_cancel(callback, state)


@router.callback_query(PortfolioFlow.mov_month, F.data == "back")
async def pf_mov_month_back(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    sign = int(data.get("mov_sign", 1))
    label, hint = ("Aporte", "entra") if sign > 0 else ("Retirada", "sale")
    await callback.message.edit_text(
        f"<b>{label}</b>: importe en EUR que {hint} de la billetera.\nEj: 500.00",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Atras", callback_data="pf:mov_back_dir"),
                InlineKeyboardButton(text="Cancelar", callback_data="pf:cancel"),
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
async def pf_mov_day_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await pf_cancel(callback, state)


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
async def pf_mov_desc_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await pf_cancel(callback, state)


def _pf_mov_confirm_text(data: dict) -> str:
    amt = data.get("mov_amount_eur", "?")
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
        await callback.message.edit_text("Error interno (datos).", reply_markup=portfolio_menu_kb())
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
            "✅ <b>Movimiento registrado</b>",
            reply_markup=portfolio_menu_kb(),
            parse_mode="HTML",
        )
    else:
        err_txt = err or "Error desconocido"
        await callback.message.edit_text(
            f"❌ <b>No se pudo registrar</b>\n\n{err_txt[:500]}",
            reply_markup=portfolio_menu_kb(),
            parse_mode="HTML",
        )

    await state.clear()
    await callback.answer()


@router.callback_query(PortfolioFlow.mov_confirm, F.data == "cancel")
async def pf_mov_confirm_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await pf_cancel(callback, state)


# Volver al resumen desde detalle
@router.callback_query(
    PortfolioFlow.consult_after_ficha,
    F.data.startswith("pw:c:"),
)
async def pf_reopen_consult_summary(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    """Boton 'Volver al resumen' desde la vista detalle."""
    parts = callback.data.split(":", 2)
    if len(parts) != 3:
        await callback.answer()
        return
    wid_raw = parts[2]
    data = await state.get_data()
    if data.get("pf_mode") != "consult" or wid_raw != data.get("wallet_id"):
        await callback.answer("Accion no valida.", show_alert=True)
        return

    try:
        wallet_id = UUID(wid_raw)
    except ValueError:
        await callback.answer()
        return

    summary = await get_wallet_summary(user.id, wallet_id)
    if not summary:
        await callback.answer("Error al recargar.", show_alert=True)
        return

    name = summary.get("wallet_name") or "Billetera"
    text = _summary_ficha_text(name, summary)
    await callback.message.edit_text(
        text,
        reply_markup=portfolio_consult_ficha_kb(wallet_id),
        parse_mode="HTML",
    )
    await callback.answer()


# --- Operacion: continuar -> activos ---


@router.callback_query(PortfolioFlow.op_after_ficha, F.data == "pf:op_assets")
async def pf_op_list_assets(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await _pf_show_assets_pick(callback, state, user)


@router.callback_query(PortfolioFlow.op_asset, F.data == "pf:op_back_ficha")
async def pf_op_back_to_ficha(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    data = await state.get_data()
    wid_raw = data.get("wallet_id")
    if not wid_raw:
        await pf_cancel(callback, state)
        return
    try:
        wallet_id = UUID(str(wid_raw))
    except ValueError:
        await pf_cancel(callback, state)
        return

    summary = await get_wallet_summary(user.id, wallet_id)
    if not summary:
        await pf_cancel(callback, state)
        return

    name = summary.get("wallet_name") or "Billetera"
    text = _summary_ficha_text(name, summary) + f"\n\n{_op_kind_label(data.get('op_api_type', 'buy'))}"
    await callback.message.edit_text(
        text,
        reply_markup=portfolio_op_ficha_kb(),
        parse_mode="HTML",
    )
    await state.set_state(PortfolioFlow.op_after_ficha)
    await callback.answer()


@router.callback_query(PortfolioFlow.op_asset, F.data.startswith("pa:"))
async def pf_pick_asset(callback: CallbackQuery, state: FSMContext) -> None:
    aid = callback.data.split(":", 1)[1]
    await state.update_data(asset_id=aid)
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
        f"Sugerido: <b>{_fmt_num(suggested)}</b>\n\n"
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
async def pf_cancel_msg(callback: CallbackQuery, state: FSMContext) -> None:
    await pf_cancel(callback, state)


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
        f"Importe total (sugerido {_fmt_num(suggested)}):\nEnvia el importe final.",
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
async def pf_op_fees_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await pf_cancel(callback, state)


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
async def pf_op_month_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await pf_cancel(callback, state)


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
async def pf_op_day_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await pf_cancel(callback, state)


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
async def pf_op_notes_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await pf_cancel(callback, state)


def _pf_op_confirm_text(data: dict) -> str:
    notes = data.get("op_notes") or "-"
    op_type = data.get("op_api_type", "buy")
    return (
        f"📌 <b>Confirmar operacion</b>\n\n"
        f"<b>Tipo:</b> {_op_kind_label(op_type)} (<code>{op_type}</code>)\n"
        f"<b>Activo ID:</b> <code>{data.get('asset_id', '?')}</code>\n"
        f"<b>Cantidad:</b> {data.get('op_quantity', '?')}\n"
        f"<b>Precio/u:</b> {data.get('op_price_per_unit', '?')}\n"
        f"<b>Total:</b> {data.get('op_total_amount', '?')}\n"
        f"<b>Comisiones:</b> {data.get('op_fees', '0')}\n"
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
        await callback.message.edit_text("Error interno (activo).", reply_markup=portfolio_menu_kb())
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
            "✅ <b>Operacion registrada</b>",
            reply_markup=portfolio_menu_kb(),
            parse_mode="HTML",
        )
    else:
        err_txt = err or "Error desconocido"
        await callback.message.edit_text(
            f"❌ <b>No se pudo registrar</b>\n\n{err_txt[:500]}",
            reply_markup=portfolio_menu_kb(),
            parse_mode="HTML",
        )

    await state.clear()
    await callback.answer()


@router.callback_query(PortfolioFlow.op_confirm, F.data == "cancel")
async def pf_op_confirm_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await pf_cancel(callback, state)
