import os
import sys
from collections.abc import AsyncGenerator
from decimal import Decimal

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.centre_test_offering import CentreTestOffering
from app.models.diagnostic_centre import DiagnosticCentre
from app.models.diagnostic_test import DiagnosticTest
from app.models.user import User
from app.utils.enums import UserRole

# Use SQLite in-memory for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    admin = User(
        email="admin@test.com",
        password_hash=hash_password("AdminPass123!"),
        full_name="System Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def normal_user(db_session: AsyncSession) -> User:
    user = User(
        email="user@test.com",
        password_hash=hash_password("UserPass123!"),
        full_name="Jane Doe",
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_headers(admin_user: User) -> dict[str, str]:
    token = create_access_token(
        subject=str(admin_user.id), role=admin_user.role.value, email=admin_user.email
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def user_headers(normal_user: User) -> dict[str, str]:
    token = create_access_token(
        subject=str(normal_user.id), role=normal_user.role.value, email=normal_user.email
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def sample_centre(db_session: AsyncSession) -> DiagnosticCentre:
    centre = DiagnosticCentre(
        name="Test Diagnostic Centre",
        address="100 Main Street",
        city="Bangalore",
        state="Karnataka",
        pincode="560001",
        is_active=True,
    )
    db_session.add(centre)
    await db_session.commit()
    await db_session.refresh(centre)
    return centre


@pytest_asyncio.fixture
async def sample_test(db_session: AsyncSession) -> DiagnosticTest:
    test = DiagnosticTest(
        name="Thyroid Profile",
        code="THYROID_TEST",
        description="Comprehensive Thyroid Check",
        category="ENDOCRINOLOGY",
        is_active=True,
    )
    db_session.add(test)
    await db_session.commit()
    await db_session.refresh(test)
    return test


@pytest_asyncio.fixture
async def sample_offering(
    db_session: AsyncSession, sample_centre: DiagnosticCentre, sample_test: DiagnosticTest
) -> CentreTestOffering:
    offering = CentreTestOffering(
        centre_id=sample_centre.id,
        test_id=sample_test.id,
        price=Decimal("850.00"),
        duration_minutes=30,
        is_available=True,
    )
    db_session.add(offering)
    await db_session.commit()
    await db_session.refresh(offering)
    return offering
