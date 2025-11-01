"""Unit tests for ExecutionAgentLogStore."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from server.services.execution.log_store import ExecutionAgentLogStore, get_execution_agent_logs


class TestExecutionAgentLogStore:
    """Test suite for ExecutionAgentLogStore class."""

    def test_create_log_store_with_user_id(self, test_data_dir, test_user_a):
        """Test ExecutionAgentLogStore creation with user_id."""
        log_store = ExecutionAgentLogStore(test_data_dir, test_user_a["id"])

        assert log_store._base_dir == test_data_dir
        assert log_store._user_id == test_user_a["id"]
        expected_user_dir = test_data_dir / "users" / test_user_a["id"] / "execution_agents"
        assert log_store._user_data_dir == expected_user_dir

    def test_get_execution_agent_logs_creates_user_specific_path(self, mock_settings, test_user_a):
        """Test get_execution_agent_logs creates correct user-specific path."""
        log_store = get_execution_agent_logs(test_user_a["id"])

        assert test_user_a["id"] in str(log_store._user_data_dir)

    def test_record_request(self, test_data_dir, test_user_a, mock_timezone):
        """Test recording agent request."""
        log_store = ExecutionAgentLogStore(test_data_dir, test_user_a["id"])
        agent_name = "test_agent"

        log_store.record_request(agent_name, "Do something")

        # Verify log file was created
        log_path = log_store._log_path(agent_name)
        assert log_path.exists()

        # Verify content
        content = log_path.read_text()
        assert "agent_request" in content
        assert "Do something" in content

    def test_record_action(self, test_data_dir, test_user_a, mock_timezone):
        """Test recording agent action."""
        log_store = ExecutionAgentLogStore(test_data_dir, test_user_a["id"])
        agent_name = "test_agent"

        log_store.record_action(agent_name, "Calling tool X")

        content = log_store._log_path(agent_name).read_text()
        assert "agent_action" in content
        assert "Calling tool X" in content

    def test_record_tool_response(self, test_data_dir, test_user_a, mock_timezone):
        """Test recording tool response."""
        log_store = ExecutionAgentLogStore(test_data_dir, test_user_a["id"])
        agent_name = "test_agent"

        log_store.record_tool_response(agent_name, "tool_name", "Success")

        content = log_store._log_path(agent_name).read_text()
        assert "tool_response" in content
        assert "tool_name" in content
        assert "Success" in content

    def test_record_agent_response(self, test_data_dir, test_user_a, mock_timezone):
        """Test recording agent response."""
        log_store = ExecutionAgentLogStore(test_data_dir, test_user_a["id"])
        agent_name = "test_agent"

        log_store.record_agent_response(agent_name, "Task completed")

        content = log_store._log_path(agent_name).read_text()
        assert "agent_response" in content
        assert "Task completed" in content

    def test_iter_entries(self, test_data_dir, test_user_a, mock_timezone):
        """Test iterating over log entries."""
        log_store = ExecutionAgentLogStore(test_data_dir, test_user_a["id"])
        agent_name = "test_agent"

        log_store.record_request(agent_name, "Request 1")
        log_store.record_action(agent_name, "Action 1")
        log_store.record_agent_response(agent_name, "Response 1")

        entries = list(log_store.iter_entries(agent_name))

        assert len(entries) == 3
        assert entries[0][0] == "agent_request"
        assert entries[0][2] == "Request 1"
        assert entries[1][0] == "agent_action"
        assert entries[1][2] == "Action 1"
        assert entries[2][0] == "agent_response"
        assert entries[2][2] == "Response 1"

    def test_load_transcript(self, test_data_dir, test_user_a, mock_timezone):
        """Test loading full transcript."""
        log_store = ExecutionAgentLogStore(test_data_dir, test_user_a["id"])
        agent_name = "test_agent"

        log_store.record_request(agent_name, "Request")
        log_store.record_agent_response(agent_name, "Response")

        transcript = log_store.load_transcript(agent_name)

        assert "agent_request" in transcript
        assert "Request" in transcript
        assert "agent_response" in transcript
        assert "Response" in transcript

    def test_load_recent_entries(self, test_data_dir, test_user_a, mock_timezone):
        """Test loading recent entries with limit."""
        log_store = ExecutionAgentLogStore(test_data_dir, test_user_a["id"])
        agent_name = "test_agent"

        # Add 20 entries
        for i in range(20):
            log_store.record_request(agent_name, f"Request {i}")

        # Load recent 5
        recent = log_store.load_recent(agent_name, limit=5)

        assert len(recent) == 5
        # Should have last 5 entries (15-19)
        assert recent[-1][2] == "Request 19"
        assert recent[0][2] == "Request 15"

    def test_list_agents(self, test_data_dir, test_user_a, mock_timezone):
        """Test listing all agents with logs."""
        log_store = ExecutionAgentLogStore(test_data_dir, test_user_a["id"])

        log_store.record_request("agent_one", "Request")
        log_store.record_request("agent_two", "Request")
        log_store.record_request("agent_three", "Request")

        agents = log_store.list_agents()

        assert len(agents) == 3
        assert "agent-one" in agents  # slugified
        assert "agent-two" in agents
        assert "agent-three" in agents

    def test_clear_all_logs(self, test_data_dir, test_user_a, mock_timezone):
        """Test clearing all execution agent logs."""
        log_store = ExecutionAgentLogStore(test_data_dir, test_user_a["id"])

        # Create logs for multiple agents
        log_store.record_request("agent_one", "Request")
        log_store.record_request("agent_two", "Request")

        # Verify logs exist
        assert len(log_store.list_agents()) == 2

        # Clear all
        log_store.clear_all()

        # Verify logs are cleared
        assert len(log_store.list_agents()) == 0

    def test_user_isolation_different_users(self, test_data_dir, test_user_a, test_user_b, mock_timezone):
        """Test that different users have separate execution logs."""
        log_store_a = ExecutionAgentLogStore(test_data_dir, test_user_a["id"])
        log_store_b = ExecutionAgentLogStore(test_data_dir, test_user_b["id"])

        # User A creates agent log
        log_store_a.record_request("my_agent", "User A's request")

        # User B creates agent log with same name
        log_store_b.record_request("my_agent", "User B's request")

        # Verify logs are separate
        entries_a = list(log_store_a.iter_entries("my_agent"))
        entries_b = list(log_store_b.iter_entries("my_agent"))

        assert len(entries_a) == 1
        assert len(entries_b) == 1
        assert entries_a[0][2] == "User A's request"
        assert entries_b[0][2] == "User B's request"

    def test_user_isolation_clear_operation(self, test_data_dir, test_user_a, test_user_b, mock_timezone):
        """Test that clear_all only affects the specific user."""
        log_store_a = ExecutionAgentLogStore(test_data_dir, test_user_a["id"])
        log_store_b = ExecutionAgentLogStore(test_data_dir, test_user_b["id"])

        # Both users create logs
        log_store_a.record_request("agent", "Request A")
        log_store_b.record_request("agent", "Request B")

        # Clear user A's logs
        log_store_a.clear_all()

        # Verify only user A's logs are cleared
        assert len(log_store_a.list_agents()) == 0
        assert len(log_store_b.list_agents()) == 1

    def test_agent_name_slugification(self, test_data_dir, test_user_a, mock_timezone):
        """Test that agent names are properly slugified."""
        log_store = ExecutionAgentLogStore(test_data_dir, test_user_a["id"])

        # Use agent name with special characters
        agent_name = "My Special Agent! @#$"
        log_store.record_request(agent_name, "Request")

        # Verify log file is created with slugified name
        agents = log_store.list_agents()
        assert len(agents) == 1
        assert agents[0] == "my-special-agent"

    def test_concurrent_writes_same_agent(self, test_data_dir, test_user_a, mock_timezone):
        """Test thread-safe concurrent writes to same agent log."""
        log_store = ExecutionAgentLogStore(test_data_dir, test_user_a["id"])
        agent_name = "concurrent_agent"

        def write_entry(num):
            log_store.record_request(agent_name, f"Request {num}")

        # Write 20 entries concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(write_entry, i) for i in range(20)]
            for future in futures:
                future.result()

        # Verify all entries were written
        entries = list(log_store.iter_entries(agent_name))
        assert len(entries) == 20

    def test_concurrent_writes_different_agents(self, test_data_dir, test_user_a, mock_timezone):
        """Test concurrent writes to different agent logs."""
        log_store = ExecutionAgentLogStore(test_data_dir, test_user_a["id"])

        def write_to_agent(agent_num):
            agent_name = f"agent_{agent_num}"
            log_store.record_request(agent_name, f"Request from agent {agent_num}")

        # Write to 10 different agents concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(write_to_agent, i) for i in range(10)]
            for future in futures:
                future.result()

        # Verify all agents have logs
        agents = log_store.list_agents()
        assert len(agents) == 10

    def test_multiline_log_entries(self, test_data_dir, test_user_a, mock_timezone):
        """Test handling of multiline log entries."""
        log_store = ExecutionAgentLogStore(test_data_dir, test_user_a["id"])
        agent_name = "test_agent"

        multiline_content = "Line 1\nLine 2\nLine 3"
        log_store.record_request(agent_name, multiline_content)

        entries = list(log_store.iter_entries(agent_name))
        assert len(entries) == 1
        assert entries[0][2] == multiline_content

    def test_special_characters_in_entries(self, test_data_dir, test_user_a, mock_timezone):
        """Test handling of special characters in log entries."""
        log_store = ExecutionAgentLogStore(test_data_dir, test_user_a["id"])
        agent_name = "test_agent"

        special_content = "Test <tag> & \"quotes\" 'apostrophes'"
        log_store.record_request(agent_name, special_content)

        entries = list(log_store.iter_entries(agent_name))
        assert len(entries) == 1
        assert entries[0][2] == special_content

