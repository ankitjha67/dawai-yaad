"""Test configuration — async fixtures for FastAPI + SQLite testing."""

import asyncio
import json
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Text, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.types import TypeDecorator

from app.database import Base, get_db
from app.main import app


# ── SQLite-compatible ARRAY shim ─────────────────────────────
# PostgreSQL ARRAY columns are stored as JSON text in SQLite tests.

class JSONArray(TypeDecorator):
    """Stores a Python list as JSON text. Used to replace ARRAY in SQLite."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None


def _patch_array_columns():
    """Replace PostgreSQL ARRAY columns with JSONArray for SQLite compat."""
    from sqlalchemy.dialects.postgresql import ARRAY
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, ARRAY):
                column.type = JSONArray()


_patch_array_columns()


# ── Test database setup ──────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///./test.db"

engine_test = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Direct database session for test setup/verification."""
    async with TestSessionLocal() as session:
        yield session
