"""Integration tests verifying user context across all API endpoints."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from server.app import app
from server.models.auth import User
from server.middleware.auth import get_current_user


class TestAPIUserContext:
    """Integration tests for user context in API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_user_a_obj(self, test_user_a):
        """Create a mock User object for user A."""
        return User(
            id=test_user_a["id"],
            email=test_user_a["email"],
            provider=test_user_a["provider"],
            created_at=datetime.utcnow()
        )

    @pytest.fixture
    def mock_user_b_obj(self, test_user_b):
        """Create a mock User object for user B."""
        return User(
            id=test_user_b["id"],
            email=test_user_b["email"],
            provider=test_user_b["provider"],
            created_at=datetime.utcnow()
        )

    def test_auth_me_returns_current_user(self, client, mock_user_a_obj):
        """Test /auth/me returns the authenticated user's information."""
        app.dependency_overrides[get_current_user] = lambda: mock_user_a_obj
        try:
            response = client.get("/api/v1/auth/me")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == mock_user_a_obj.id
        assert data["email"] == mock_user_a_obj.email
        assert data["provider"] == mock_user_a_obj.provider

    def test_auth_me_different_users(self, client, mock_user_a_obj, mock_user_b_obj):
        """Test /auth/me returns correct data for different users."""
        # User A
        app.dependency_overrides[get_current_user] = lambda: mock_user_a_obj
        try:
            response_a = client.get("/api/v1/auth/me")
        finally:
            app.dependency_overrides.clear()

        # User B
        app.dependency_overrides[get_current_user] = lambda: mock_user_b_obj
        try:
            response_b = client.get("/api/v1/auth/me")
        finally:
            app.dependency_overrides.clear()

        data_a = response_a.json()
        data_b = response_b.json()

        assert data_a["id"] == mock_user_a_obj.id
        assert data_b["id"] == mock_user_b_obj.id
        assert data_a["email"] != data_b["email"]

    def test_chat_history_uses_correct_user_context(self, client, mock_user_a_obj, mock_settings, mock_timezone):
        """Test that chat history endpoint uses correct user context."""
        from server.services.conversation.log import get_conversation_log
        from server.middleware.auth import get_current_user
        from server.app import app

        # Setup: Add message for user A
        conv_log = get_conversation_log(mock_user_a_obj.id)
        conv_log.record_user_message("Test message")

        # Override the dependency to return user A
        app.dependency_overrides[get_current_user] = lambda: mock_user_a_obj
        try:
            response = client.get("/api/v1/chat/history")

            assert response.status_code == 200
            data = response.json()
            assert len(data["messages"]) == 1
            assert data["messages"][0]["content"] == "Test message"
        finally:
            app.dependency_overrides.clear()

    def test_protected_endpoints_require_authentication(self, client):
        """Test that protected endpoints require authentication."""
        from server.middleware.auth import get_current_user
        from server.app import app
        
        protected_endpoints = [
            ("/api/v1/auth/me", "GET"),
            ("/api/v1/chat/history", "GET"),
            ("/api/v1/chat/history", "DELETE"),
        ]

        def raise_auth_error():
            raise Exception("Not authenticated")

        for endpoint, method in protected_endpoints:
            # Mock authentication failure
            app.dependency_overrides[get_current_user] = raise_auth_error
            try:
                if method == "GET":
                    with pytest.raises(Exception):
                        client.get(endpoint)
                elif method == "DELETE":
                    with pytest.raises(Exception):
                        client.delete(endpoint)
            finally:
                app.dependency_overrides.clear()

    def test_user_context_in_concurrent_requests(self, client, mock_user_a_obj, mock_user_b_obj, mock_settings, mock_timezone):
        """Test that user context is correctly maintained across sequential requests."""
        # Note: Testing data isolation sequentially, not true HTTP concurrency,
        # because app.dependency_overrides is global state that doesn't handle
        # concurrent access well in tests. The actual application uses JWT tokens
        # which are per-request and don't have this global state issue.
        from server.services.conversation.log import get_conversation_log
        from server.middleware.auth import get_current_user
        from server.app import app

        # Setup: Both users have different messages
        conv_log_a = get_conversation_log(mock_user_a_obj.id)
        conv_log_b = get_conversation_log(mock_user_b_obj.id)
        
        conv_log_a.record_user_message("User A unique message")
        conv_log_b.record_user_message("User B unique message")

        # Fetch as User A
        app.dependency_overrides[get_current_user] = lambda: mock_user_a_obj
        try:
            response_a = client.get("/api/v1/chat/history")
        finally:
            app.dependency_overrides.clear()

        # Fetch as User B
        app.dependency_overrides[get_current_user] = lambda: mock_user_b_obj
        try:
            response_b = client.get("/api/v1/chat/history")
        finally:
            app.dependency_overrides.clear()

        # Verify each got their own data
        data_a = response_a.json()
        data_b = response_b.json()

        assert "User A unique message" in str(data_a["messages"])
        assert "User B unique message" not in str(data_a["messages"])
        
        assert "User B unique message" in str(data_b["messages"])
        assert "User A unique message" not in str(data_b["messages"])

    def test_user_cannot_access_other_user_data_via_api(self, client, mock_user_a_obj, mock_user_b_obj, mock_settings, mock_timezone):
        """Test that user A cannot access user B's data through API."""
        from server.services.conversation.log import get_conversation_log
        from server.middleware.auth import get_current_user
        from server.app import app

        # Setup: User B has private data
        conv_log_b = get_conversation_log(mock_user_b_obj.id)
        conv_log_b.record_user_message("User B secret message")

        # User A tries to access data (but will only see their own empty history)
        app.dependency_overrides[get_current_user] = lambda: mock_user_a_obj
        try:
            response = client.get("/api/v1/chat/history")

            data = response.json()
            # User A should not see User B's message
            assert "User B secret message" not in str(data["messages"])
            # User A should see empty history
            assert len(data["messages"]) == 0
        finally:
            app.dependency_overrides.clear()

    def test_logout_endpoint_accessible(self, client, mock_user_a_obj):
        """Test that logout endpoint is accessible."""
        from server.middleware.auth import get_current_user
        from server.app import app

        app.dependency_overrides[get_current_user] = lambda: mock_user_a_obj
        try:
            response = client.post("/api/v1/auth/logout")

            assert response.status_code == 200
            data = response.json()
            assert "message" in data
        finally:
            app.dependency_overrides.clear()

    def test_meta_endpoint_does_not_leak_user_data(self, client):
        """Test that meta endpoints don't leak user-specific data."""
        # Meta endpoints like server status should not expose user data
        # This is a placeholder test - adjust based on actual meta endpoints
        response = client.get("/api/v1/meta/status")
        
        if response.status_code == 200:
            # If the endpoint exists, verify it doesn't contain user IDs or emails
            data = response.json()
            assert "test_user_a" not in str(data).lower()
            assert "test_user_b" not in str(data).lower()

    def test_user_context_persists_across_multiple_operations(self, client, mock_user_a_obj, mock_settings, mock_timezone):
        """Test that user context is maintained across multiple operations."""
        from server.services.conversation.log import get_conversation_log
        from server.services.execution.roster import get_agent_roster
        from server.middleware.auth import get_current_user
        from server.app import app

        # Perform multiple operations as user A
        app.dependency_overrides[get_current_user] = lambda: mock_user_a_obj
        try:
            # Add data through the service layer (simulating what routes would do)
            conv_log = get_conversation_log(mock_user_a_obj.id)
            roster = get_agent_roster(mock_user_a_obj.id)
            
            conv_log.record_user_message("Message 1")
            roster.add_agent("agent_1")
            
            conv_log.record_user_message("Message 2")
            roster.add_agent("agent_2")
            
            # Fetch history
            response = client.get("/api/v1/chat/history")

            data = response.json()
            # Should have both messages
            assert len(data["messages"]) == 2
            
            # Verify roster is correct
            agents = roster.get_agents()
            assert len(agents) == 2
            assert "agent_1" in agents
            assert "agent_2" in agents
        finally:
            app.dependency_overrides.clear()

    def test_different_users_same_session(self, client, mock_user_a_obj, mock_user_b_obj, mock_settings, mock_timezone):
        """Test handling different users in the same test session."""
        from server.services.conversation.log import get_conversation_log
        from server.middleware.auth import get_current_user
        from server.app import app

        # User A creates message
        conv_log_a = get_conversation_log(mock_user_a_obj.id)
        conv_log_a.record_user_message("User A session message")

        # Fetch as User A
        app.dependency_overrides[get_current_user] = lambda: mock_user_a_obj
        try:
            response_a = client.get("/api/v1/chat/history")
        finally:
            app.dependency_overrides.clear()

        # User B creates message
        conv_log_b = get_conversation_log(mock_user_b_obj.id)
        conv_log_b.record_user_message("User B session message")

        # Fetch as User B
        app.dependency_overrides[get_current_user] = lambda: mock_user_b_obj
        try:
            response_b = client.get("/api/v1/chat/history")
        finally:
            app.dependency_overrides.clear()

        # Verify correct data for each user
        data_a = response_a.json()
        data_b = response_b.json()

        assert len(data_a["messages"]) == 1
        assert len(data_b["messages"]) == 1
        assert data_a["messages"][0]["content"] == "User A session message"
        assert data_b["messages"][0]["content"] == "User B session message"

    def test_admin_user_has_own_context(self, client, test_user_admin, mock_settings):
        """Test that admin user has their own isolated context."""
        from server.middleware.auth import get_current_user
        from server.app import app

        mock_admin_obj = User(
            id=test_user_admin["id"],
            email=test_user_admin["email"],
            provider=test_user_admin["provider"],
            created_at=datetime.utcnow()
        )

        app.dependency_overrides[get_current_user] = lambda: mock_admin_obj
        try:
            response = client.get("/api/v1/auth/me")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "admin"
            assert data["email"] == "admin@openpoke.local"
            assert data["provider"] == "system"
        finally:
            app.dependency_overrides.clear()

