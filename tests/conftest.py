"""Test configuration and fixtures."""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app import models  # Import models to ensure they're registered with Base

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Use StaticPool to maintain single connection
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Register a SQLite-compatible to_char so services.py works in tests
@event.listens_for(engine, "connect")
def register_functions(dbapi_conn, connection_record):
    dbapi_conn.create_function("to_char", 2, lambda dt, fmt: dt[:7] if dt else None)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """Test client with a fresh in-memory database per test."""
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
