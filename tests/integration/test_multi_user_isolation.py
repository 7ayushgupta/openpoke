"""Integration tests for multi-user data isolation."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from server.services.conversation.log import get_conversation_log
from server.services.execution.log_store import get_execution_agent_logs
from server.services.execution.roster import get_agent_roster
from server.services.triggers import get_trigger_service


class TestMultiUserIsolation:
    """Integration tests verifying complete user data isolation."""

    def test_complete_isolation_scenario(self, mock_settings, test_user_a, test_user_b, mock_timezone):
        """Test complete user isolation across all services."""
        # User A operations
        conv_log_a = get_conversation_log(test_user_a["id"])
        exec_logs_a = get_execution_agent_logs(test_user_a["id"])
        roster_a = get_agent_roster(test_user_a["id"])
        trigger_service_a = get_trigger_service(test_user_a["id"])

        # User B operations
        conv_log_b = get_conversation_log(test_user_b["id"])
        exec_logs_b = get_execution_agent_logs(test_user_b["id"])
        roster_b = get_agent_roster(test_user_b["id"])
        trigger_service_b = get_trigger_service(test_user_b["id"])

        # User A creates data
        conv_log_a.record_user_message("User A message")
        exec_logs_a.record_request("agent_a", "User A task")
        roster_a.add_agent("agent_a")
        trigger_a = trigger_service_a.create_trigger(
            agent_name="agent_a",
            payload="User A trigger",
            start_time="2025-12-01T10:00:00"
        )

        # User B creates data
        conv_log_b.record_user_message("User B message")
        exec_logs_b.record_request("agent_b", "User B task")
        roster_b.add_agent("agent_b")
        trigger_b = trigger_service_b.create_trigger(
            agent_name="agent_b",
            payload="User B trigger",
            start_time="2025-12-01T11:00:00"
        )

        # Verify conversation logs are separate
        messages_a = conv_log_a.to_chat_messages()
        messages_b = conv_log_b.to_chat_messages()
        assert len(messages_a) == 1
        assert len(messages_b) == 1
        assert messages_a[0].content == "User A message"
        assert messages_b[0].content == "User B message"

        # Verify execution logs are separate
        entries_a = list(exec_logs_a.iter_entries("agent_a"))
        entries_b = list(exec_logs_b.iter_entries("agent_b"))
        assert len(entries_a) == 1
        assert len(entries_b) == 1
        assert entries_a[0][2] == "User A task"
        assert entries_b[0][2] == "User B task"

        # Verify rosters are separate
        agents_a = roster_a.get_agents()
        agents_b = roster_b.get_agents()
        assert "agent_a" in agents_a
        assert "agent_b" in agents_b
        assert "agent_b" not in agents_a
        assert "agent_a" not in agents_b

        # Verify triggers are separate
        triggers_a = trigger_service_a.list_triggers(agent_name="agent_a")
        triggers_b = trigger_service_b.list_triggers(agent_name="agent_b")
        assert len(triggers_a) == 1
        assert len(triggers_b) == 1
        assert triggers_a[0].user_id == test_user_a["id"]
        assert triggers_b[0].user_id == test_user_b["id"]

    def test_clear_operations_isolation(self, mock_settings, test_user_a, test_user_b, mock_timezone):
        """Test that clear operations only affect the target user."""
        # Setup: Both users create data
        conv_log_a = get_conversation_log(test_user_a["id"])
        conv_log_b = get_conversation_log(test_user_b["id"])
        exec_logs_a = get_execution_agent_logs(test_user_a["id"])
        exec_logs_b = get_execution_agent_logs(test_user_b["id"])
        roster_a = get_agent_roster(test_user_a["id"])
        roster_b = get_agent_roster(test_user_b["id"])
        trigger_service_a = get_trigger_service(test_user_a["id"])
        trigger_service_b = get_trigger_service(test_user_b["id"])

        # Both users create data
        conv_log_a.record_user_message("Message A")
        conv_log_b.record_user_message("Message B")
        exec_logs_a.record_request("agent", "Task A")
        exec_logs_b.record_request("agent", "Task B")
        roster_a.add_agent("agent_a")
        roster_b.add_agent("agent_b")
        trigger_service_a.create_trigger(
            agent_name="agent",
            payload="Trigger A",
            start_time="2025-12-01T10:00:00"
        )
        trigger_service_b.create_trigger(
            agent_name="agent",
            payload="Trigger B",
            start_time="2025-12-01T11:00:00"
        )

        # Clear user A's data
        conv_log_a.clear()
        exec_logs_a.clear_all()
        roster_a.clear()
        trigger_service_a.clear_all()

        # Verify user A's data is cleared
        assert len(conv_log_a.to_chat_messages()) == 0
        assert len(exec_logs_a.list_agents()) == 0
        assert len(roster_a.get_agents()) == 0
        assert len(trigger_service_a.list_triggers(agent_name="agent")) == 0

        # Verify user B's data is untouched
        assert len(conv_log_b.to_chat_messages()) == 1
        assert len(exec_logs_b.list_agents()) == 1
        assert len(roster_b.get_agents()) == 1
        assert len(trigger_service_b.list_triggers(agent_name="agent")) == 1

    def test_concurrent_operations_different_users(self, mock_settings, test_user_a, test_user_b, mock_timezone):
        """Test concurrent operations by different users don't interfere."""
        def user_a_operations():
            conv_log = get_conversation_log(test_user_a["id"])
            exec_logs = get_execution_agent_logs(test_user_a["id"])
            roster = get_agent_roster(test_user_a["id"])
            
            for i in range(10):
                conv_log.record_user_message(f"User A message {i}")
                exec_logs.record_request("agent_a", f"User A task {i}")
                roster.add_agent(f"agent_a_{i}")

        def user_b_operations():
            conv_log = get_conversation_log(test_user_b["id"])
            exec_logs = get_execution_agent_logs(test_user_b["id"])
            roster = get_agent_roster(test_user_b["id"])
            
            for i in range(10):
                conv_log.record_user_message(f"User B message {i}")
                exec_logs.record_request("agent_b", f"User B task {i}")
                roster.add_agent(f"agent_b_{i}")

        # Run operations concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(user_a_operations)
            future_b = executor.submit(user_b_operations)
            future_a.result()
            future_b.result()

        # Verify both users have their data
        conv_log_a = get_conversation_log(test_user_a["id"])
        conv_log_b = get_conversation_log(test_user_b["id"])
        exec_logs_a = get_execution_agent_logs(test_user_a["id"])
        exec_logs_b = get_execution_agent_logs(test_user_b["id"])
        roster_a = get_agent_roster(test_user_a["id"])
        roster_b = get_agent_roster(test_user_b["id"])

        assert len(conv_log_a.to_chat_messages()) == 10
        assert len(conv_log_b.to_chat_messages()) == 10
        assert "agent-a" in exec_logs_a.list_agents()
        assert "agent-b" in exec_logs_b.list_agents()
        assert len(roster_a.get_agents()) == 10
        assert len(roster_b.get_agents()) == 10

    def test_same_agent_name_different_users(self, mock_settings, test_user_a, test_user_b, mock_timezone):
        """Test that users can use same agent names without conflict."""
        # Both users use the same agent name
        agent_name = "my_special_agent"

        exec_logs_a = get_execution_agent_logs(test_user_a["id"])
        exec_logs_b = get_execution_agent_logs(test_user_b["id"])
        roster_a = get_agent_roster(test_user_a["id"])
        roster_b = get_agent_roster(test_user_b["id"])
        trigger_service_a = get_trigger_service(test_user_a["id"])
        trigger_service_b = get_trigger_service(test_user_b["id"])

        # Both users create data with same agent name
        exec_logs_a.record_request(agent_name, "Task for user A")
        exec_logs_b.record_request(agent_name, "Task for user B")
        roster_a.add_agent(agent_name)
        roster_b.add_agent(agent_name)
        trigger_service_a.create_trigger(
            agent_name=agent_name,
            payload="Trigger for user A",
            start_time="2025-12-01T10:00:00"
        )
        trigger_service_b.create_trigger(
            agent_name=agent_name,
            payload="Trigger for user B",
            start_time="2025-12-01T11:00:00"
        )

        # Verify data is separate despite same agent name
        entries_a = list(exec_logs_a.iter_entries(agent_name))
        entries_b = list(exec_logs_b.iter_entries(agent_name))
        assert entries_a[0][2] == "Task for user A"
        assert entries_b[0][2] == "Task for user B"

        triggers_a = trigger_service_a.list_triggers(agent_name=agent_name)
        triggers_b = trigger_service_b.list_triggers(agent_name=agent_name)
        assert triggers_a[0].payload == "Trigger for user A"
        assert triggers_b[0].payload == "Trigger for user B"

    def test_file_system_path_isolation(self, mock_settings, test_user_a, test_user_b):
        """Test that user data is stored in separate filesystem paths."""
        conv_log_a = get_conversation_log(test_user_a["id"])
        conv_log_b = get_conversation_log(test_user_b["id"])
        exec_logs_a = get_execution_agent_logs(test_user_a["id"])
        exec_logs_b = get_execution_agent_logs(test_user_b["id"])
        roster_a = get_agent_roster(test_user_a["id"])
        roster_b = get_agent_roster(test_user_b["id"])

        # Verify paths contain user IDs
        assert test_user_a["id"] in str(conv_log_a._path)
        assert test_user_b["id"] in str(conv_log_b._path)
        assert test_user_a["id"] in str(exec_logs_a._user_data_dir)
        assert test_user_b["id"] in str(exec_logs_b._user_data_dir)
        assert test_user_a["id"] in str(roster_a._user_roster_path)
        assert test_user_b["id"] in str(roster_b._user_roster_path)

        # Verify paths are different
        assert conv_log_a._path != conv_log_b._path
        assert exec_logs_a._user_data_dir != exec_logs_b._user_data_dir
        assert roster_a._user_roster_path != roster_b._user_roster_path

    def test_user_specific_working_memory(self, mock_settings, test_user_a, test_user_b, mock_timezone):
        """Test that working memory logs are user-specific."""
        conv_log_a = get_conversation_log(test_user_a["id"])
        conv_log_b = get_conversation_log(test_user_b["id"])

        # Both users record messages
        conv_log_a.record_user_message("User A question")
        conv_log_a.record_reply("User A answer")
        conv_log_b.record_user_message("User B question")
        conv_log_b.record_reply("User B answer")

        # Verify working memory logs are separate
        assert conv_log_a._working_memory_log != conv_log_b._working_memory_log
        
        # Verify user IDs are correctly set
        assert conv_log_a._user_id == test_user_a["id"]
        assert conv_log_b._user_id == test_user_b["id"]

    def test_bulk_operations_isolation(self, mock_settings, mock_timezone):
        """Test isolation with multiple users performing bulk operations."""
        user_ids = [f"bulk_user_{i}" for i in range(5)]
        
        # Each user creates 20 items across different services
        for user_id in user_ids:
            conv_log = get_conversation_log(user_id)
            exec_logs = get_execution_agent_logs(user_id)
            roster = get_agent_roster(user_id)
            
            for i in range(20):
                conv_log.record_user_message(f"{user_id} message {i}")
                exec_logs.record_request(f"agent_{i}", f"{user_id} task {i}")
                roster.add_agent(f"agent_{i}")

        # Verify each user has exactly their data
        for user_id in user_ids:
            conv_log = get_conversation_log(user_id)
            exec_logs = get_execution_agent_logs(user_id)
            roster = get_agent_roster(user_id)
            
            messages = conv_log.to_chat_messages()
            agents = exec_logs.list_agents()
            roster_agents = roster.get_agents()
            
            assert len(messages) == 20
            assert len(agents) == 20
            assert len(roster_agents) == 20
            
            # Verify content belongs to correct user
            assert all(user_id in msg.content for msg in messages)

