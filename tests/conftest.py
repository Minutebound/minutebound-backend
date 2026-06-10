import pytest
from fastapi.testclient import TestClient
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db
from app.api.v1.deps import get_current_user
from app.db.models import User
from app.core.security import get_password_hash


@pytest.fixture(autouse=True)
async def clear_cache():
    try:
        FastAPICache.init(InMemoryBackend(), prefix="test-cache")
    except Exception:
        pass
    yield
    try:
        await FastAPICache.clear()
    except Exception:
        pass

# In-memory database -- created and destroyed post each test
TEST_DATABASE_URL = "sqlite:///./minutbound_test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user(db):
    user = User(
        id = 1,
        email = "test@test.com",
        hashed_password = get_password_hash("password"),
        full_name = "Test User"
    )
    db.add(user)
    db.commit()
    return user

@pytest.fixture
def auth_client(db, test_user):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: test_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def client():
    """
    Creates a TestClient for every test case.
    This resolves the 'fixture client not found' error.
    """
    with TestClient(app) as c:
        yield c

