"""Pytest configuration and fixtures for OpenPoke tests."""

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Generator

import pytest
from pydantic import BaseModel

# Add server directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test data."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def test_data_dir(temp_dir: Path) -> Path:
    """Create a test data directory structure."""
    data_dir = temp_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def test_user_a():
    """Test user A fixture."""
    return {
        "id": "test_user_a",
        "email": "user_a@test.com",
        "provider": "google",
    }


@pytest.fixture
def test_user_b():
    """Test user B fixture."""
    return {
        "id": "test_user_b",
        "email": "user_b@test.com",
        "provider": "google",
    }


@pytest.fixture
def test_user_admin():
    """Test admin user fixture."""
    return {
        "id": "admin",
        "email": "admin@openpoke.local",
        "provider": "system",
    }


@pytest.fixture
def mock_user_db(test_data_dir: Path) -> Path:
    """Create a mock user database."""
    db_path = test_data_dir / "users.db"
    return db_path


@pytest.fixture
def mock_settings(test_data_dir: Path, monkeypatch):
    """Mock settings with test data directory."""
    # Mock the data directory
    from server.services.conversation import log as conversation_log_module
    from server.services.execution import log_store as execution_log_module
    from server.services.execution import roster as roster_module
    from server.services.conversation.summarization import working_memory_log as wm_log_module
    
    monkeypatch.setattr(conversation_log_module, "_DATA_DIR", test_data_dir)
    monkeypatch.setattr(execution_log_module, "_DATA_DIR", test_data_dir)
    monkeypatch.setattr(roster_module, "_DATA_DIR", test_data_dir)
    monkeypatch.setattr(wm_log_module, "_DATA_DIR", test_data_dir)
    
    return test_data_dir


@pytest.fixture
def test_user_store(mock_user_db: Path):
    """Create a test user store instance."""
    from server.services.auth.user_store import UserStore
    
    return UserStore(mock_user_db)


@pytest.fixture
def populated_user_store(test_user_store, test_user_a, test_user_b):
    """Create a user store with test users already added."""
    from server.models.auth import UserCreate
    
    # Create test users
    test_user_store.create_user(UserCreate(**test_user_a))
    test_user_store.create_user(UserCreate(**test_user_b))
    
    return test_user_store


@pytest.fixture
def mock_jwt_token():
    """Mock JWT token for testing."""
    return "mock_jwt_token_for_testing"


@pytest.fixture
def mock_current_user(test_user_a):
    """Mock current user for dependency injection."""
    from server.models.auth import User
    
    return User(
        id=test_user_a["id"],
        email=test_user_a["email"],
        provider=test_user_a["provider"],
        created_at=datetime.utcnow()
    )


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # This prevents state leakage between tests
    yield
    # Cleanup happens after each test


@pytest.fixture
def mock_timezone(monkeypatch):
    """Mock timezone to a consistent value for testing."""
    monkeypatch.setenv("TZ", "UTC")
    return "UTC"

