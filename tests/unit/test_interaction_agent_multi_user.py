"""Unit tests for multi-user support in interaction agent."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from server.agents.interaction_agent.agent import (
    _render_active_agents,
    prepare_message_with_history,
)
from server.services.execution import AgentRoster


class TestInteractionAgentMultiUser:
    """Test suite for interaction agent multi-user support."""

    def test_render_active_agents_requires_user_id(self, test_data_dir, test_user_a):
        """Test that _render_active_agents requires user_id parameter."""
        # This test ensures the function signature requires user_id
        roster = AgentRoster(test_data_dir, test_user_a["id"])
        roster.add_agent("test_agent")
        
        # Should work with user_id
        result = _render_active_agents(test_user_a["id"])
        assert "test_agent" in result

    def test_render_active_agents_no_agents(self, test_data_dir, test_user_a):
        """Test rendering when no agents are active."""
        result = _render_active_agents(test_user_a["id"])
        assert result == "None"

    def test_render_active_agents_single_agent(self, test_data_dir, test_user_a):
        """Test rendering with a single active agent."""
        roster = AgentRoster(test_data_dir, test_user_a["id"])
        roster.add_agent("email_agent")
        
        result = _render_active_agents(test_user_a["id"])
        assert '<agent name="email_agent" />' in result

    def test_render_active_agents_multiple_agents(self, test_data_dir, test_user_a):
        """Test rendering with multiple active agents."""
        roster = AgentRoster(test_data_dir, test_user_a["id"])
        roster.add_agent("email_agent")
        roster.add_agent("calendar_agent")
        roster.add_agent("search_agent")
        
        result = _render_active_agents(test_user_a["id"])
        assert '<agent name="email_agent" />' in result
        assert '<agent name="calendar_agent" />' in result
        assert '<agent name="search_agent" />' in result

    def test_render_active_agents_escapes_special_chars(self, test_data_dir, test_user_a):
        """Test that agent names with special characters are escaped."""
        roster = AgentRoster(test_data_dir, test_user_a["id"])
        roster.add_agent('agent"with"quotes')
        
        result = _render_active_agents(test_user_a["id"])
        # Should escape the quotes
        assert "agent&quot;with&quot;quotes" in result

    def test_render_active_agents_user_isolation(self, test_data_dir, test_user_a, test_user_b):
        """Test that active agents are properly isolated between users."""
        roster_a = AgentRoster(test_data_dir, test_user_a["id"])
        roster_b = AgentRoster(test_data_dir, test_user_b["id"])
        
        # User A has different agents than User B
        roster_a.add_agent("user_a_agent")
        roster_b.add_agent("user_b_agent")
        
        result_a = _render_active_agents(test_user_a["id"])
        result_b = _render_active_agents(test_user_b["id"])
        
        # Each user should only see their own agents
        assert "user_a_agent" in result_a
        assert "user_b_agent" not in result_a
        
        assert "user_b_agent" in result_b
        assert "user_a_agent" not in result_b

    def test_prepare_message_with_history_requires_user_id(self, test_data_dir, test_user_a):
        """Test that prepare_message_with_history requires user_id parameter."""
        # Should work with user_id
        messages = prepare_message_with_history(
            "Hello", 
            "Previous conversation", 
            test_user_a["id"],
            message_type="user"
        )
        
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "Hello" in messages[0]["content"]

    def test_prepare_message_with_history_user_message(self, test_data_dir, test_user_a):
        """Test preparing user message with history."""
        messages = prepare_message_with_history(
            "What's the weather?",
            "Previous: User asked about time",
            test_user_a["id"],
            message_type="user"
        )
        
        content = messages[0]["content"]
        assert "<conversation_history>" in content
        assert "Previous: User asked about time" in content
        assert "<active_agents>" in content
        assert "<new_user_message>" in content
        assert "What's the weather?" in content

    def test_prepare_message_with_history_agent_message(self, test_data_dir, test_user_a):
        """Test preparing agent message with history."""
        messages = prepare_message_with_history(
            "Email sent successfully",
            "Previous conversation",
            test_user_a["id"],
            message_type="agent"
        )
        
        content = messages[0]["content"]
        assert "<new_agent_message>" in content
        assert "Email sent successfully" in content
        assert "<new_user_message>" not in content

    def test_prepare_message_with_history_includes_active_agents(self, test_data_dir, test_user_a):
        """Test that prepared messages include active agents for the user."""
        roster = AgentRoster(test_data_dir, test_user_a["id"])
        roster.add_agent("email_agent")
        
        messages = prepare_message_with_history(
            "Check my email",
            "",
            test_user_a["id"],
            message_type="user"
        )
        
        content = messages[0]["content"]
        assert "<active_agents>" in content
        assert "email_agent" in content

    def test_prepare_message_with_history_empty_transcript(self, test_data_dir, test_user_a):
        """Test preparing message with empty conversation history."""
        messages = prepare_message_with_history(
            "First message",
            "",
            test_user_a["id"],
            message_type="user"
        )
        
        content = messages[0]["content"]
        assert "<conversation_history>\nNone\n</conversation_history>" in content

    def test_prepare_message_with_history_user_isolation(self, test_data_dir, test_user_a, test_user_b):
        """Test that prepared messages respect user isolation."""
        # User A has an agent
        roster_a = AgentRoster(test_data_dir, test_user_a["id"])
        roster_a.add_agent("user_a_email_agent")
        
        # User B has a different agent
        roster_b = AgentRoster(test_data_dir, test_user_b["id"])
        roster_b.add_agent("user_b_calendar_agent")
        
        # Prepare messages for both users
        messages_a = prepare_message_with_history(
            "Check email", 
            "User A conversation", 
            test_user_a["id"],
            message_type="user"
        )
        messages_b = prepare_message_with_history(
            "Check calendar", 
            "User B conversation", 
            test_user_b["id"],
            message_type="user"
        )
        
        content_a = messages_a[0]["content"]
        content_b = messages_b[0]["content"]
        
        # User A should see their agent, not User B's
        assert "user_a_email_agent" in content_a
        assert "user_b_calendar_agent" not in content_a
        
        # User B should see their agent, not User A's
        assert "user_b_calendar_agent" in content_b
        assert "user_a_email_agent" not in content_b


class TestInteractionRuntimeMultiUser:
    """Test suite for InteractionAgentRuntime multi-user support."""

    @pytest.mark.asyncio
    async def test_runtime_initialization_with_user_id(self, mock_settings, test_user_a, monkeypatch):
        """Test that InteractionAgentRuntime properly initializes with user_id."""
        # Mock required services and API key
        monkeypatch.setenv("OPENAI_API_KEY", "test_key")
        
        from server.agents.interaction_agent.runtime import InteractionAgentRuntime
        
        runtime = InteractionAgentRuntime(test_user_a["id"])
        
        assert runtime.user_id == test_user_a["id"]
        assert runtime.conversation_log is not None
        assert runtime.working_memory_log is not None

    @pytest.mark.asyncio
    async def test_runtime_uses_user_specific_logs(self, mock_settings, test_user_a, test_user_b, monkeypatch):
        """Test that different runtime instances use user-specific logs."""
        monkeypatch.setenv("OPENAI_API_KEY", "test_key")
        
        from server.agents.interaction_agent.runtime import InteractionAgentRuntime
        
        runtime_a = InteractionAgentRuntime(test_user_a["id"])
        runtime_b = InteractionAgentRuntime(test_user_b["id"])
        
        # Each runtime should have different log instances
        assert runtime_a.user_id == test_user_a["id"]
        assert runtime_b.user_id == test_user_b["id"]
        
        # Logs should be separate
        assert runtime_a.conversation_log != runtime_b.conversation_log
        assert runtime_a.working_memory_log != runtime_b.working_memory_log


class TestSummarizationMultiUser:
    """Test suite for summarization multi-user support."""

    @pytest.mark.asyncio
    async def test_schedule_summarization_requires_user_id(self, mock_settings, test_user_a):
        """Test that schedule_summarization requires user_id."""
        from server.services.conversation.summarization import schedule_summarization
        
        # Should not raise error with user_id
        schedule_summarization(test_user_a["id"])

    @pytest.mark.asyncio
    async def test_schedule_summarization_per_user(self, mock_settings, test_user_a, test_user_b):
        """Test that summarization is scheduled per user."""
        from server.services.conversation.summarization.scheduler import _pending_users, schedule_summarization
        
        # Clear any pending state
        _pending_users.clear()
        
        # Schedule for both users
        schedule_summarization(test_user_a["id"])
        schedule_summarization(test_user_b["id"])
        
        # Both users should be in pending
        assert test_user_a["id"] in _pending_users
        assert test_user_b["id"] in _pending_users

    @pytest.mark.asyncio
    async def test_summarize_conversation_requires_user_id(self, mock_settings, test_user_a, monkeypatch):
        """Test that summarize_conversation requires user_id."""
        from server.services.conversation.summarization.summarizer import summarize_conversation
        
        # Mock to prevent actual LLM calls
        async def mock_call(*args, **kwargs):
            return "mock summary"
        
        monkeypatch.setattr(
            "server.services.conversation.summarization.summarizer._call_llm",
            mock_call
        )
        
        # Disable summarization to avoid actual execution
        monkeypatch.setattr(
            "server.config.Settings.summarization_enabled", 
            property(lambda self: False)
        )
        
        # Should not raise error with user_id
        result = await summarize_conversation(test_user_a["id"])
        assert result is False  # Returns False when disabled


@pytest.fixture(autouse=True)
def setup_mock_settings(mock_settings):
    """Automatically use mock settings for all tests in this module."""
    return mock_settings

