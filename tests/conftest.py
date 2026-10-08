"""Shared isolated test setup."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_ROOT = Path(__file__).parent / ".test_runtime"
TEST_ROOT.mkdir(exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{(TEST_ROOT / 'test.db').as_posix()}"
os.environ["STORAGE_PATH"] = str(TEST_ROOT / "storage")
os.environ["MAX_RECIPIENTS"] = "3"

from app.config import get_settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database() -> None:
    """Reset tables and files so every test starts from a clean state."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    settings = get_settings()
    storage = Path(settings.storage_path)
    if storage.exists():
        for path in sorted(storage.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
    storage.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient without relying on startup timing for worker tests."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Provide a direct session for assertions."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
