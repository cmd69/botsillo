import logging
from datetime import date
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
