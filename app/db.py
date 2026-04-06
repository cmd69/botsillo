from sqlalchemy import BigInteger, Column, String, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

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
