"""
Pytest fixtures for backend API testing.
"""

import os
import sys
from pathlib import Path
from typing import Generator
import uuid

import pytest
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, SessionLocal, engine, get_db
from app.main import app
from app.models import SessionModel, MessageModel


@pytest.fixture(scope="session")
def db_engine():
    """Ensure database schema is created on test database."""
    Base.metadata.create_all(bind=engine)
    yield engine


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator:
    """Provides a transactional database session for each test."""
    session = SessionLocal()
    created_session_ids = []

    try:
        yield session
    finally:
        # Clean up any test sessions created during test
        for s_id in created_session_ids:
            try:
                s = session.query(SessionModel).filter(SessionModel.id == s_id).first()
                if s:
                    session.delete(s)
                    session.commit()
            except Exception:
                session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(db_session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with database session dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
