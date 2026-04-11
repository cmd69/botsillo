import logging
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx

from app.auth import create_bot_token
from app.config import settings

log = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=settings.API_BASE_URL,
            timeout=10.0,
        )
    return _client


def _headers(user_id: UUID) -> dict:
    return {"Authorization": f"Bearer {create_bot_token(user_id)}"}


def _http_error_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict) and "detail" in data:
            detail = data["detail"]
            if isinstance(detail, list):
                parts = []
                for item in detail:
                    if isinstance(item, dict) and "msg" in item:
                        parts.append(str(item["msg"]))
                    else:
                        parts.append(str(item))
                return "; ".join(parts) if parts else response.text
            return str(detail)
    except Exception:
        pass
    return (response.text or response.reason_phrase or "Error HTTP").strip() or "Error HTTP"


def _decimal_json(x: Decimal | float | int | str) -> str:
    if isinstance(x, Decimal):
        return format(x, "f")
    return str(x)


async def create_transaction(
    user_id: UUID,
    tx_type: str,
    amount: float,
    tx_date: date,
    category_id: UUID | None = None,
    description: str | None = None,
) -> dict | None:
    payload = {
        "type": tx_type,
        "amount": amount,
        "date": tx_date.isoformat(),
    }
    if category_id:
        payload["category_id"] = str(category_id)
    if description:
        payload["description"] = description

    try:
        resp = await _get_client().post(
            "/api/v1/transactions/",
            json=payload,
            headers=_headers(user_id),
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        log.error("Error creando transaccion: %s — %s", e, getattr(e, 'response', None) and e.response.text)
        return None


async def get_categories(user_id: UUID) -> list[dict]:
    """Obtiene todas las categorias del usuario (raiz + hijas)."""
    try:
        resp = await _get_client().get(
            "/api/v1/categories/",
            headers=_headers(user_id),
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        log.error("Error obteniendo categorias: %s — %s", e, getattr(e, 'response', None) and e.response.text)
        return []


async def get_summary(user_id: UUID, year_month: str) -> dict | None:
    try:
        resp = await _get_client().get(
            "/api/v1/transactions/summary",
            headers=_headers(user_id),
            params={"year_month": year_month},
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        log.error("Error obteniendo resumen: %s", e)
        return None


async def get_transactions(
    user_id: UUID, limit: int = 100, year_month: str | None = None,
) -> list[dict]:
    params: dict = {"limit": limit}
    if year_month:
        params["year_month"] = year_month
    try:
        resp = await _get_client().get(
            "/api/v1/transactions/",
            headers=_headers(user_id),
            params=params,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        log.error("Error obteniendo transacciones: %s", e)
        return []


async def list_investment_wallets(user_id: UUID) -> list[dict]:
    try:
        resp = await _get_client().get(
            "/api/v1/investments/wallets",
            headers=_headers(user_id),
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        log.error(
            "Error listando billeteras: %s — %s",
            e,
            getattr(e, "response", None) and e.response.text,
        )
        return []


async def get_wallet_summary(user_id: UUID, wallet_id: UUID) -> dict | None:
    try:
        resp = await _get_client().get(
            f"/api/v1/investments/wallets/{wallet_id}/summary",
            headers=_headers(user_id),
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        log.error(
            "Error resumen billetera: %s — %s",
            e,
            getattr(e, "response", None) and e.response.text,
        )
        return None


async def get_wallet_details(user_id: UUID, wallet_id: UUID) -> dict | None:
    try:
        resp = await _get_client().get(
            f"/api/v1/investments/wallets/{wallet_id}/details",
            headers=_headers(user_id),
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        log.error(
            "Error detalle billetera: %s — %s",
            e,
            getattr(e, "response", None) and e.response.text,
        )
        return None


async def list_wallet_assets(user_id: UUID, wallet_id: UUID) -> list[dict]:
    try:
        resp = await _get_client().get(
            f"/api/v1/investments/wallets/{wallet_id}/assets",
            headers=_headers(user_id),
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        log.error(
            "Error listando activos: %s — %s",
            e,
            getattr(e, "response", None) and e.response.text,
        )
        return []


async def create_asset_operation(
    user_id: UUID,
    asset_id: UUID,
    op_type: str,
    quantity: Decimal,
    price_per_unit: Decimal,
    total_amount: Decimal,
    fees: Decimal,
    op_date: date,
    notes: str | None = None,
) -> tuple[dict | None, str | None]:
    """POST /investments/assets/{asset_id}/operations. Devuelve (data, error_mensaje)."""
    payload: dict[str, Any] = {
        "asset_id": str(asset_id),
        "type": op_type,
        "quantity": _decimal_json(quantity),
        "price_per_unit": _decimal_json(price_per_unit),
        "total_amount": _decimal_json(total_amount),
        "fees": _decimal_json(fees),
        "date": op_date.isoformat(),
    }
    if notes:
        payload["notes"] = notes

    try:
        resp = await _get_client().post(
            f"/api/v1/investments/assets/{asset_id}/operations",
            json=payload,
            headers=_headers(user_id),
        )
        if resp.status_code >= 400:
            err = _http_error_detail(resp)
            log.error("Error creando operacion activo: %s — %s", resp.status_code, err)
            return None, err
        return resp.json(), None
    except httpx.HTTPError as e:
        msg = getattr(e, "response", None) and e.response.text or str(e)
        log.error("Error creando operacion activo: %s", e)
        return None, msg
