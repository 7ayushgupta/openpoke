"""User storage service for multi-user support."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ...logging_config import logger
from ...models.auth import User, UserCreate


class UserStore:
    """SQLite-based user storage."""
    
    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._ensure_directory()
        self._ensure_schema()
        self._create_admin_user()
    
    def _ensure_directory(self) -> None:
        """Ensure database directory exists."""
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning(
                "user database directory creation failed",
                extra={"error": str(exc), "path": str(self._db_path.parent)},
            )
    
    def _ensure_schema(self) -> None:
        """Create users table if it doesn't exist."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            provider TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
        index_sql = """
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """
        
        with self._lock, self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(schema_sql)
            conn.execute(index_sql)
    
    def _connect(self) -> sqlite3.Connection:
        """Create database connection."""
        conn = sqlite3.connect(self._db_path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _create_admin_user(self) -> None:
        """Create default admin user if it doesn't exist."""
        try:
            admin_user = self.get_user_by_id("admin")
            if admin_user is None:
                self.create_user(UserCreate(
                    id="admin",
                    email="admin@openpoke.local",
                    provider="system"
                ))
                logger.info("Created default admin user")
        except Exception as exc:
            logger.warning(f"Failed to create admin user: {exc}")
    
    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        user = User(
            id=user_data.id,
            email=user_data.email,
            provider=user_data.provider,
            created_at=datetime.utcnow()
        )
        
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO users (id, email, provider, created_at) VALUES (?, ?, ?, ?)",
                (user.id, user.email, user.provider, user.created_at.isoformat())
            )
        
        logger.info(f"Created user: {user.email} ({user.id})")
        return user
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()
        
        if row is None:
            return None
        
        return User(
            id=row["id"],
            email=row["email"],
            provider=row["provider"],
            created_at=datetime.fromisoformat(row["created_at"])
        )
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,)
            ).fetchone()
        
        if row is None:
            return None
        
        return User(
            id=row["id"],
            email=row["email"],
            provider=row["provider"],
            created_at=datetime.fromisoformat(row["created_at"])
        )
    
    def list_users(self) -> List[User]:
        """List all users."""
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM users ORDER BY created_at ASC"
            ).fetchall()
        
        return [
            User(
                id=row["id"],
                email=row["email"],
                provider=row["provider"],
                created_at=datetime.fromisoformat(row["created_at"])
            )
            for row in rows
        ]
    
    def user_exists(self, user_id: str) -> bool:
        """Check if user exists."""
        return self.get_user_by_id(user_id) is not None


# Global user store instance
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_USER_DB_PATH = _DATA_DIR / "users.db"
_user_store = UserStore(_USER_DB_PATH)


def get_user_store() -> UserStore:
    """Get the singleton user store instance."""
    return _user_store


__all__ = ["UserStore", "get_user_store"]

