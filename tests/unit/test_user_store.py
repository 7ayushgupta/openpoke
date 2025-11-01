"""Unit tests for UserStore."""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pytest
from server.models.auth import User, UserCreate
from server.services.auth.user_store import UserStore


class TestUserStore:
    """Test suite for UserStore class."""

    def test_create_user_success(self, test_user_store, test_user_a):
        """Test successful user creation."""
        user_data = UserCreate(**test_user_a)
        user = test_user_store.create_user(user_data)

        assert user.id == test_user_a["id"]
        assert user.email == test_user_a["email"]
        assert user.provider == test_user_a["provider"]
        assert isinstance(user.created_at, datetime)

    def test_create_user_duplicate_id(self, test_user_store, test_user_a):
        """Test creating user with duplicate ID fails."""
        user_data = UserCreate(**test_user_a)
        test_user_store.create_user(user_data)

        # Try to create user with same ID
        with pytest.raises(Exception):  # Should raise sqlite3.IntegrityError
            test_user_store.create_user(user_data)

    def test_create_user_duplicate_email(self, test_user_store, test_user_a):
        """Test creating user with duplicate email fails."""
        user_data = UserCreate(**test_user_a)
        test_user_store.create_user(user_data)

        # Try to create different user with same email
        duplicate_email_data = UserCreate(
            id="different_id",
            email=test_user_a["email"],
            provider="google"
        )
        with pytest.raises(Exception):  # Should raise sqlite3.IntegrityError
            test_user_store.create_user(duplicate_email_data)

    def test_get_user_by_id_exists(self, test_user_store, test_user_a):
        """Test retrieving existing user by ID."""
        user_data = UserCreate(**test_user_a)
        created_user = test_user_store.create_user(user_data)

        retrieved_user = test_user_store.get_user_by_id(test_user_a["id"])

        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == created_user.email
        assert retrieved_user.provider == created_user.provider

    def test_get_user_by_id_not_exists(self, test_user_store):
        """Test retrieving non-existent user by ID returns None."""
        retrieved_user = test_user_store.get_user_by_id("nonexistent_user")
        assert retrieved_user is None

    def test_get_user_by_email_exists(self, test_user_store, test_user_a):
        """Test retrieving existing user by email."""
        user_data = UserCreate(**test_user_a)
        created_user = test_user_store.create_user(user_data)

        retrieved_user = test_user_store.get_user_by_email(test_user_a["email"])

        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == created_user.email

    def test_get_user_by_email_not_exists(self, test_user_store):
        """Test retrieving non-existent user by email returns None."""
        retrieved_user = test_user_store.get_user_by_email("nonexistent@test.com")
        assert retrieved_user is None

    def test_list_users_empty(self, test_user_store):
        """Test listing users when database is empty (only admin)."""
        users = test_user_store.list_users()
        # Should have the default admin user
        assert len(users) == 1
        assert users[0].id == "admin"

    def test_list_users_multiple(self, populated_user_store):
        """Test listing multiple users."""
        users = populated_user_store.list_users()
        
        # Should have admin + 2 test users
        assert len(users) >= 2
        user_ids = [user.id for user in users]
        assert "test_user_a" in user_ids
        assert "test_user_b" in user_ids

    def test_user_exists_true(self, test_user_store, test_user_a):
        """Test user_exists returns True for existing user."""
        user_data = UserCreate(**test_user_a)
        test_user_store.create_user(user_data)

        assert test_user_store.user_exists(test_user_a["id"]) is True

    def test_user_exists_false(self, test_user_store):
        """Test user_exists returns False for non-existent user."""
        assert test_user_store.user_exists("nonexistent_user") is False

    def test_default_admin_user_created(self, test_user_store):
        """Test that default admin user is created automatically."""
        admin_user = test_user_store.get_user_by_id("admin")
        
        assert admin_user is not None
        assert admin_user.id == "admin"
        assert admin_user.email == "admin@openpoke.local"
        assert admin_user.provider == "system"

    def test_concurrent_user_creation(self, mock_user_db):
        """Test thread-safe concurrent user creation."""
        store = UserStore(mock_user_db)
        results = []
        errors = []

        def create_user(user_num):
            try:
                user_data = UserCreate(
                    id=f"concurrent_user_{user_num}",
                    email=f"user{user_num}@test.com",
                    provider="google"
                )
                user = store.create_user(user_data)
                results.append(user)
            except Exception as e:
                errors.append(e)

        # Create 10 users concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_user, i) for i in range(10)]
            for future in futures:
                future.result()

        # Verify all users were created successfully
        assert len(results) == 10
        assert len(errors) == 0

        # Verify all users are in the database
        all_users = store.list_users()
        user_ids = [user.id for user in all_users]
        for i in range(10):
            assert f"concurrent_user_{i}" in user_ids

    def test_concurrent_read_operations(self, populated_user_store):
        """Test thread-safe concurrent read operations."""
        results = []
        
        def read_user(user_id):
            user = populated_user_store.get_user_by_id(user_id)
            results.append(user)
        
        # Read same user concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(read_user, "test_user_a") for _ in range(20)]
            for future in futures:
                future.result()
        
        # All reads should succeed
        assert len(results) == 20
        assert all(user is not None for user in results)
        assert all(user.id == "test_user_a" for user in results)

    def test_database_persistence(self, mock_user_db, test_user_a):
        """Test that data persists across store instances."""
        # Create user with first store instance
        store1 = UserStore(mock_user_db)
        user_data = UserCreate(**test_user_a)
        store1.create_user(user_data)

        # Create new store instance and verify user exists
        store2 = UserStore(mock_user_db)
        retrieved_user = store2.get_user_by_id(test_user_a["id"])

        assert retrieved_user is not None
        assert retrieved_user.id == test_user_a["id"]
        assert retrieved_user.email == test_user_a["email"]

