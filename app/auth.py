import logging
from datetime import datetime
from uuid import UUID

from jose import JWTError, jwt

from app.config import settings

log = logging.getLogger(__name__)


def decode_link_token(token: str) -> UUID | None:
    """Decodifica un JWT de vinculacion (purpose=telegram_link).

    Retorna el user_id (UUID) si el token es valido, None en caso contrario.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        log.warning("JWT invalido en vinculacion")
        return None

    if payload.get("purpose") != "telegram_link":
        log.warning("JWT sin purpose=telegram_link")
        return None

    sub = payload.get("sub")
    if not sub:
        return None

    try:
        return UUID(sub)
    except ValueError:
        return None


def create_bot_token(user_id: UUID) -> str:
    """Crea un JWT para que el bot autentique contra la API de expensivo."""
    payload = {
        "sub": str(user_id),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
