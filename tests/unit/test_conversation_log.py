"""Unit tests for ConversationLog."""

from pathlib import Path

import pytest
from server.services.conversation.log import ConversationLog, get_conversation_log


class TestConversationLog:
    """Test suite for ConversationLog class."""

    def test_create_conversation_log_with_user_id(self, test_data_dir, test_user_a, mock_settings):
        """Test ConversationLog creation with user_id."""
        log_path = test_data_dir / "users" / test_user_a["id"] / "conversation" / "test.log"
        log = ConversationLog(log_path, test_user_a["id"])

        assert log._path == log_path
        assert log._user_id == test_user_a["id"]
        assert log._working_memory_log is not None

    def test_get_conversation_log_creates_user_specific_path(self, mock_settings, test_user_a):
        """Test get_conversation_log creates correct user-specific path."""
        log = get_conversation_log(test_user_a["id"])

        expected_path_suffix = Path("users") / test_user_a["id"] / "conversation" / "poke_conversation.log"
        assert str(expected_path_suffix) in str(log._path)
        assert log._user_id == test_user_a["id"]

    def test_record_user_message(self, test_data_dir, test_user_a, mock_settings, mock_timezone):
        """Test recording user message."""
        log_path = test_data_dir / "users" / test_user_a["id"] / "conversation" / "test.log"
        log = ConversationLog(log_path, test_user_a["id"])

        log.record_user_message("Hello, this is a test message")

        # Verify message was written to file
        assert log_path.exists()
        content = log_path.read_text()
        assert "user_message" in content
        assert "Hello, this is a test message" in content

    def test_record_agent_message(self, test_data_dir, test_user_a, mock_settings, mock_timezone):
        """Test recording agent message."""
        log_path = test_data_dir / "users" / test_user_a["id"] / "conversation" / "test.log"
        log = ConversationLog(log_path, test_user_a["id"])

        log.record_agent_message("Agent response message")

        # Verify message was written to file
        assert log_path.exists()
        content = log_path.read_text()
        assert "agent_message" in content
        assert "Agent response message" in content

    def test_record_reply(self, test_data_dir, test_user_a, mock_settings, mock_timezone):
        """Test recording reply message."""
        log_path = test_data_dir / "users" / test_user_a["id"] / "conversation" / "test.log"
        log = ConversationLog(log_path, test_user_a["id"])

        log.record_reply("Poke reply message")

        # Verify message was written to file
        assert log_path.exists()
        content = log_path.read_text()
        assert "poke_reply" in content
        assert "Poke reply message" in content

    def test_record_wait(self, test_data_dir, test_user_a, mock_settings, mock_timezone):
        """Test recording wait marker."""
        log_path = test_data_dir / "users" / test_user_a["id"] / "conversation" / "test.log"
        log = ConversationLog(log_path, test_user_a["id"])

        log.record_wait("Waiting for execution agent")

        # Verify wait was written to file
        assert log_path.exists()
        content = log_path.read_text()
        assert "wait" in content
        assert "Waiting for execution agent" in content

    def test_to_chat_messages_excludes_wait(self, test_data_dir, test_user_a, mock_settings, mock_timezone):
        """Test that to_chat_messages excludes wait markers."""
        log_path = test_data_dir / "users" / test_user_a["id"] / "conversation" / "test.log"
        log = ConversationLog(log_path, test_user_a["id"])

        log.record_user_message("User message")
        log.record_wait("Wait marker - should be excluded")
        log.record_reply("Assistant reply")

        messages = log.to_chat_messages()

        # Should have 2 messages (user and assistant, no wait)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "User message"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Assistant reply"

    def test_user_isolation_different_logs(self, test_data_dir, test_user_a, test_user_b, mock_settings, mock_timezone):
        """Test that different users have separate log files."""
        log_a = get_conversation_log(test_user_a["id"])
        log_b = get_conversation_log(test_user_b["id"])

        # Write to user A's log
        log_a.record_user_message("Message from user A")

        # Write to user B's log
        log_b.record_user_message("Message from user B")

        # Verify logs are separate
        messages_a = log_a.to_chat_messages()
        messages_b = log_b.to_chat_messages()

        assert len(messages_a) == 1
        assert len(messages_b) == 1
        assert messages_a[0].content == "Message from user A"
        assert messages_b[0].content == "Message from user B"

    def test_clear_log(self, test_data_dir, test_user_a, mock_settings, mock_timezone):
        """Test clearing conversation log."""
        log_path = test_data_dir / "users" / test_user_a["id"] / "conversation" / "test.log"
        log = ConversationLog(log_path, test_user_a["id"])

        # Add some messages
        log.record_user_message("Message 1")
        log.record_reply("Reply 1")

        # Verify messages exist
        assert len(log.to_chat_messages()) == 2

        # Clear log
        log.clear()

        # Verify log is empty
        messages = log.to_chat_messages()
        assert len(messages) == 0

    def test_load_transcript(self, test_data_dir, test_user_a, mock_settings, mock_timezone):
        """Test loading transcript from log."""
        log_path = test_data_dir / "users" / test_user_a["id"] / "conversation" / "test.log"
        log = ConversationLog(log_path, test_user_a["id"])

        log.record_user_message("Test message")
        log.record_reply("Test reply")

        transcript = log.load_transcript()

        assert "user_message" in transcript
        assert "Test message" in transcript
        assert "poke_reply" in transcript
        assert "Test reply" in transcript

    def test_iter_entries(self, test_data_dir, test_user_a, mock_settings, mock_timezone):
        """Test iterating over log entries."""
        log_path = test_data_dir / "users" / test_user_a["id"] / "conversation" / "test.log"
        log = ConversationLog(log_path, test_user_a["id"])

        log.record_user_message("Message 1")
        log.record_reply("Reply 1")

        entries = list(log.iter_entries())

        assert len(entries) == 2
        assert entries[0][0] == "user_message"  # tag
        assert entries[0][2] == "Message 1"  # payload
        assert entries[1][0] == "poke_reply"
        assert entries[1][2] == "Reply 1"

    def test_directory_creation(self, test_data_dir, test_user_a, mock_settings):
        """Test that log directory is created automatically."""
        log_path = test_data_dir / "users" / test_user_a["id"] / "deep" / "nested" / "path" / "test.log"
        log = ConversationLog(log_path, test_user_a["id"])

        log.record_user_message("Test")

        # Verify nested directory was created
        assert log_path.parent.exists()
        assert log_path.exists()

    def test_multiline_messages(self, test_data_dir, test_user_a, mock_settings, mock_timezone):
        """Test handling of multiline messages."""
        log_path = test_data_dir / "users" / test_user_a["id"] / "conversation" / "test.log"
        log = ConversationLog(log_path, test_user_a["id"])

        multiline_message = "Line 1\nLine 2\nLine 3"
        log.record_user_message(multiline_message)

        messages = log.to_chat_messages()
        assert len(messages) == 1
        assert messages[0].content == multiline_message

    def test_special_characters_in_messages(self, test_data_dir, test_user_a, mock_settings, mock_timezone):
        """Test handling of special characters."""
        log_path = test_data_dir / "users" / test_user_a["id"] / "conversation" / "test.log"
        log = ConversationLog(log_path, test_user_a["id"])

        special_message = "Test <tag> & \"quotes\" 'apostrophes'"
        log.record_user_message(special_message)

        messages = log.to_chat_messages()
        assert len(messages) == 1
        assert messages[0].content == special_message

