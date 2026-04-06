from uuid import UUID

from jose import jwt

from app.config import settings


def create_bot_token(user_id: UUID) -> str:
    """Crea un JWT para que el bot autentique contra la API de expensivo."""
    payload = {"sub": str(user_id)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
