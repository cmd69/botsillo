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
    token = create_bot_token(user_id)
    return {"Authorization": f"Bearer {token}"}


async def create_transaction(
    user_id: UUID,
    tx_type: str,
    amount: float,
    tx_date: date,
    category_id: UUID | None = None,
    description: str | None = None,
) -> dict | None:
    """Crea una transaccion via API. Retorna el dict o None si falla."""
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
    except httpx.HTTPError:
        log.exception("Error creando transaccion")
        return None


async def get_categories(user_id: UUID) -> list[dict]:
    """Obtiene categorias del usuario via API."""
    try:
        resp = await _get_client().get(
            "/api/v1/categories/",
            headers=_headers(user_id),
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError:
        log.exception("Error obteniendo categorias")
        return []
