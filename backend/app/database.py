"""Dawai Yaad — Database Connection & Session."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# ── Async engine (FastAPI) ───────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Sync engine (Celery tasks) ───────────────────────────────
# Lazy-initialized to avoid importing psycopg2 in test environments.

_sync_engine = None
_SyncSessionLocal = None


def get_sync_session_factory():
    """Get or create the sync session factory (lazy init)."""
    global _sync_engine, _SyncSessionLocal

    if _SyncSessionLocal is None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session, sessionmaker

        _sync_engine = create_engine(
            settings.database_url_sync,
            echo=False,
            pool_size=5,
            max_overflow=5,
            pool_pre_ping=True,
        )
        _SyncSessionLocal = sessionmaker(
            _sync_engine,
            class_=Session,
            expire_on_commit=False,
        )

    return _SyncSessionLocal


class SyncSessionLocal:
    """Context manager wrapping the lazy sync session factory.

    Usage:
        with SyncSessionLocal() as db:
            db.execute(...)
            db.commit()
    """

    def __enter__(self):
        factory = get_sync_session_factory()
        self._session = factory()
        return self._session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._session.rollback()
        self._session.close()
        return False
