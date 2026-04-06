import logging
from uuid import UUID

from sqlalchemy import BigInteger, Column, DateTime, String, select, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

log = logging.getLogger(__name__)

_engine = None
_async_session = None


def _get_session_factory():
    global _engine, _async_session
    if _engine is None:
        _engine = create_async_engine(settings.DATABASE_URL, echo=False)
        _async_session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _async_session


class Base(DeclarativeBase):
    pass


class User(Base):
    """Espejo read-only del modelo User de expensivo."""
    __tablename__ = "user"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    username = Column(String, nullable=False)
    telegram_chat_id = Column(BigInteger, unique=True, nullable=True)


async def get_user_by_chat_id(chat_id: int) -> User | None:
    async with _get_session_factory()() as session:
        result = await session.execute(
            select(User).where(User.telegram_chat_id == chat_id)
        )
        return result.scalar_one_or_none()


async def get_user_by_id(user_id: UUID) -> User | None:
    async with _get_session_factory()() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()


async def link_telegram(user_id: UUID, chat_id: int) -> bool:
    """Guarda el telegram_chat_id en el usuario. Retorna True si OK."""
    async with _get_session_factory()() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return False
        user.telegram_chat_id = chat_id
        await session.commit()
        return True


async def check_db() -> bool:
    try:
        async with _get_session_factory()() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        log.exception("DB health check failed")
        return False
