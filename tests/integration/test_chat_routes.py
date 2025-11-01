"""Integration tests for chat routes with mocked authentication."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from server.app import app
from server.models.auth import User
from server.middleware.auth import get_current_user
from server.services.conversation.log import get_conversation_log


class TestChatRoutes:
    """Integration tests for chat routes."""

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

    def test_chat_history_with_user_a(self, client, mock_user_a_obj, mock_settings, mock_timezone):
        """Test GET /chat/history returns user A's data."""
        # Setup: Add messages for user A
        conv_log = get_conversation_log(mock_user_a_obj.id)
        conv_log.record_user_message("User A message 1")
        conv_log.record_reply("User A reply 1")

        # Mock authentication to return user A
        app.dependency_overrides[get_current_user] = lambda: mock_user_a_obj
        try:
            response = client.get("/api/v1/chat/history")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert len(data["messages"]) == 2
        assert data["messages"][0]["content"] == "User A message 1"
        assert data["messages"][1]["content"] == "User A reply 1"

    def test_chat_history_with_user_b(self, client, mock_user_b_obj, mock_settings, mock_timezone):
        """Test GET /chat/history returns user B's data."""
        # Setup: Add messages for user B
        conv_log = get_conversation_log(mock_user_b_obj.id)
        conv_log.record_user_message("User B message 1")
        conv_log.record_reply("User B reply 1")

        # Mock authentication to return user B
        app.dependency_overrides[get_current_user] = lambda: mock_user_b_obj
        try:
            response = client.get("/api/v1/chat/history")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 2
        assert data["messages"][0]["content"] == "User B message 1"
        assert data["messages"][1]["content"] == "User B reply 1"

    def test_chat_history_isolation(self, client, mock_user_a_obj, mock_user_b_obj, mock_settings, mock_timezone):
        """Test that users only see their own chat history."""
        # Setup: Both users have messages
        conv_log_a = get_conversation_log(mock_user_a_obj.id)
        conv_log_b = get_conversation_log(mock_user_b_obj.id)
        
        conv_log_a.record_user_message("User A private message")
        conv_log_b.record_user_message("User B private message")

        # User A fetches history
        app.dependency_overrides[get_current_user] = lambda: mock_user_a_obj
        try:
            response_a = client.get("/api/v1/chat/history")
        finally:
            app.dependency_overrides.clear()

        # User B fetches history
        app.dependency_overrides[get_current_user] = lambda: mock_user_b_obj
        try:
            response_b = client.get("/api/v1/chat/history")
        finally:
            app.dependency_overrides.clear()

        # Verify isolation
        data_a = response_a.json()
        data_b = response_b.json()

        assert "User A private message" in str(data_a["messages"])
        assert "User B private message" not in str(data_a["messages"])
        
        assert "User B private message" in str(data_b["messages"])
        assert "User A private message" not in str(data_b["messages"])

    def test_clear_history_user_a(self, client, mock_user_a_obj, mock_user_b_obj, mock_settings, mock_timezone):
        """Test DELETE /chat/history only clears requesting user's data."""
        # Setup: Both users have messages
        conv_log_a = get_conversation_log(mock_user_a_obj.id)
        conv_log_b = get_conversation_log(mock_user_b_obj.id)
        
        conv_log_a.record_user_message("User A message")
        conv_log_b.record_user_message("User B message")

        # User A clears history
        app.dependency_overrides[get_current_user] = lambda: mock_user_a_obj
        try:
            response = client.delete("/api/v1/chat/history")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200

        # Verify user A's history is cleared
        messages_a = conv_log_a.to_chat_messages()
        assert len(messages_a) == 0

        # Verify user B's history is untouched
        messages_b = conv_log_b.to_chat_messages()
        assert len(messages_b) == 1
        assert messages_b[0].content == "User B message"

    def test_clear_history_user_b(self, client, mock_user_a_obj, mock_user_b_obj, mock_settings, mock_timezone):
        """Test DELETE /chat/history for user B doesn't affect user A."""
        # Setup: Both users have messages
        conv_log_a = get_conversation_log(mock_user_a_obj.id)
        conv_log_b = get_conversation_log(mock_user_b_obj.id)
        
        conv_log_a.record_user_message("User A message")
        conv_log_b.record_user_message("User B message")

        # User B clears history
        app.dependency_overrides[get_current_user] = lambda: mock_user_b_obj
        try:
            response = client.delete("/api/v1/chat/history")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200

        # Verify user B's history is cleared
        messages_b = conv_log_b.to_chat_messages()
        assert len(messages_b) == 0

        # Verify user A's history is untouched
        messages_a = conv_log_a.to_chat_messages()
        assert len(messages_a) == 1
        assert messages_a[0].content == "User A message"

    def test_clear_history_clears_all_user_data(self, client, mock_user_a_obj, mock_settings, mock_timezone):
        """Test that clear history clears conversation, execution logs, roster, and triggers."""
        from server.services.execution.log_store import get_execution_agent_logs
        from server.services.execution.roster import get_agent_roster
        from server.services.triggers import get_trigger_service

        # Setup: User A has data in all services
        conv_log = get_conversation_log(mock_user_a_obj.id)
        exec_logs = get_execution_agent_logs(mock_user_a_obj.id)
        roster = get_agent_roster(mock_user_a_obj.id)
        trigger_service = get_trigger_service(mock_user_a_obj.id)

        conv_log.record_user_message("Message")
        exec_logs.record_request("agent", "Task")
        roster.add_agent("agent")
        trigger_service.create_trigger(
            agent_name="agent",
            payload="Task",
            start_time="2025-12-01T10:00:00"
        )

        # Clear history
        app.dependency_overrides[get_current_user] = lambda: mock_user_a_obj
        try:
            response = client.delete("/api/v1/chat/history")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200

        # Reload instances to get updated state
        conv_log = get_conversation_log(mock_user_a_obj.id)
        exec_logs = get_execution_agent_logs(mock_user_a_obj.id)
        roster = get_agent_roster(mock_user_a_obj.id)
        trigger_service = get_trigger_service(mock_user_a_obj.id)

        # Verify all data is cleared
        assert len(conv_log.to_chat_messages()) == 0
        assert len(exec_logs.list_agents()) == 0
        assert len(roster.get_agents()) == 0
        assert len(trigger_service.list_triggers(agent_name="agent")) == 0

    def test_authentication_required_for_history(self, client):
        """Test that authentication is required to access chat history."""
        import pytest
        # Try to access history without authentication
        def raise_auth_error():
            raise Exception("Not authenticated")
        
        app.dependency_overrides[get_current_user] = raise_auth_error
        try:
            with pytest.raises(Exception, match="Not authenticated"):
                client.get("/api/v1/chat/history")
        finally:
            app.dependency_overrides.clear()

    def test_authentication_required_for_clear(self, client):
        """Test that authentication is required to clear history."""
        import pytest
        # Try to clear history without authentication
        def raise_auth_error():
            raise Exception("Not authenticated")
        
        app.dependency_overrides[get_current_user] = raise_auth_error
        try:
            with pytest.raises(Exception, match="Not authenticated"):
                client.delete("/api/v1/chat/history")
        finally:
            app.dependency_overrides.clear()

    def test_empty_history_for_new_user(self, client, mock_user_a_obj, mock_settings):
        """Test that new users start with empty history."""
        # Mock authentication for a new user with no history
        app.dependency_overrides[get_current_user] = lambda: mock_user_a_obj
        try:
            response = client.get("/api/v1/chat/history")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert len(data["messages"]) == 0

    def test_chat_history_preserves_message_order(self, client, mock_user_a_obj, mock_settings, mock_timezone):
        """Test that chat history preserves message order."""
        # Setup: Add multiple messages in sequence
        conv_log = get_conversation_log(mock_user_a_obj.id)
        conv_log.record_user_message("Message 1")
        conv_log.record_reply("Reply 1")
        conv_log.record_user_message("Message 2")
        conv_log.record_reply("Reply 2")
        conv_log.record_user_message("Message 3")
        conv_log.record_reply("Reply 3")

        # Fetch history
        app.dependency_overrides[get_current_user] = lambda: mock_user_a_obj
        try:
            response = client.get("/api/v1/chat/history")
        finally:
            app.dependency_overrides.clear()

        data = response.json()
        messages = data["messages"]

        # Verify order is preserved
        assert len(messages) == 6
        assert messages[0]["content"] == "Message 1"
        assert messages[1]["content"] == "Reply 1"
        assert messages[2]["content"] == "Message 2"
        assert messages[3]["content"] == "Reply 2"
        assert messages[4]["content"] == "Message 3"
        assert messages[5]["content"] == "Reply 3"

    def test_multiple_clears_do_not_error(self, client, mock_user_a_obj, mock_settings, mock_timezone):
        """Test that clearing history multiple times doesn't cause errors."""
        # Clear history multiple times
        app.dependency_overrides[get_current_user] = lambda: mock_user_a_obj
        try:
            response1 = client.delete("/api/v1/chat/history")
            response2 = client.delete("/api/v1/chat/history")
            response3 = client.delete("/api/v1/chat/history")
        finally:
            app.dependency_overrides.clear()

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200

    def test_concurrent_history_access(self, client, mock_user_a_obj, mock_user_b_obj, mock_settings, mock_timezone):
        """Test that different users can access their own history without interference."""
        # Note: We're testing data isolation, not HTTP concurrency, due to
        # app.dependency_overrides being a global state that doesn't handle
        # true concurrency well in tests. The actual application uses JWT tokens
        # which are per-request and don't have this issue.

        # Setup: Both users have messages
        conv_log_a = get_conversation_log(mock_user_a_obj.id)
        conv_log_b = get_conversation_log(mock_user_b_obj.id)
        
        conv_log_a.record_user_message("User A message")
        conv_log_b.record_user_message("User B message")

        # Fetch User A's history
        app.dependency_overrides[get_current_user] = lambda: mock_user_a_obj
        try:
            response_a = client.get("/api/v1/chat/history")
        finally:
            app.dependency_overrides.clear()

        # Fetch User B's history
        app.dependency_overrides[get_current_user] = lambda: mock_user_b_obj
        try:
            response_b = client.get("/api/v1/chat/history")
        finally:
            app.dependency_overrides.clear()

        # Both should succeed
        assert response_a.status_code == 200
        assert response_b.status_code == 200

        # Verify correct data returned for each user
        data_a = response_a.json()
        data_b = response_b.json()
        assert "User A message" in str(data_a["messages"])
        assert "User B message" in str(data_b["messages"])
        
        # Verify no cross-contamination
        assert "User B message" not in str(data_a["messages"])
        assert "User A message" not in str(data_b["messages"])

