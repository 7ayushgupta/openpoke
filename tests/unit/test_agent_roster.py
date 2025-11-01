"""Unit tests for AgentRoster."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from server.services.execution.roster import AgentRoster, get_agent_roster


class TestAgentRoster:
    """Test suite for AgentRoster class."""

    def test_create_roster_with_user_id(self, test_data_dir, test_user_a):
        """Test AgentRoster creation with user_id."""
        roster = AgentRoster(test_data_dir, test_user_a["id"])

        assert roster._user_id == test_user_a["id"]
        expected_path = test_data_dir / "users" / test_user_a["id"] / "execution_agents" / "roster.json"
        assert roster._user_roster_path == expected_path

    def test_get_agent_roster_creates_user_specific_path(self, mock_settings, test_user_a):
        """Test get_agent_roster creates correct user-specific path."""
        roster = get_agent_roster(test_user_a["id"])

        assert test_user_a["id"] in str(roster._user_roster_path)

    def test_add_agent(self, test_data_dir, test_user_a):
        """Test adding agent to roster."""
        roster = AgentRoster(test_data_dir, test_user_a["id"])

        roster.add_agent("test_agent_1")

        assert "test_agent_1" in roster.get_agents()
        assert len(roster.get_agents()) == 1

    def test_add_multiple_agents(self, test_data_dir, test_user_a):
        """Test adding multiple agents to roster."""
        roster = AgentRoster(test_data_dir, test_user_a["id"])

        roster.add_agent("agent_1")
        roster.add_agent("agent_2")
        roster.add_agent("agent_3")

        agents = roster.get_agents()
        assert len(agents) == 3
        assert "agent_1" in agents
        assert "agent_2" in agents
        assert "agent_3" in agents

    def test_add_duplicate_agent(self, test_data_dir, test_user_a):
        """Test adding duplicate agent (should not create duplicates)."""
        roster = AgentRoster(test_data_dir, test_user_a["id"])

        roster.add_agent("test_agent")
        roster.add_agent("test_agent")  # Add same agent again

        agents = roster.get_agents()
        # Should only have one instance
        assert agents.count("test_agent") == 1

    def test_remove_agent(self, test_data_dir, test_user_a):
        """Test removing agent from roster."""
        roster = AgentRoster(test_data_dir, test_user_a["id"])

        roster.add_agent("agent_1")
        roster.add_agent("agent_2")
        roster.remove_agent("agent_1")

        agents = roster.get_agents()
        assert len(agents) == 1
        assert "agent_1" not in agents
        assert "agent_2" in agents

    def test_remove_nonexistent_agent(self, test_data_dir, test_user_a):
        """Test removing agent that doesn't exist (should not error)."""
        roster = AgentRoster(test_data_dir, test_user_a["id"])

        roster.add_agent("agent_1")
        roster.remove_agent("nonexistent_agent")  # Should not raise error

        agents = roster.get_agents()
        assert len(agents) == 1
        assert "agent_1" in agents

    def test_clear_roster(self, test_data_dir, test_user_a):
        """Test clearing all agents from roster."""
        roster = AgentRoster(test_data_dir, test_user_a["id"])

        roster.add_agent("agent_1")
        roster.add_agent("agent_2")
        roster.add_agent("agent_3")

        assert len(roster.get_agents()) == 3

        roster.clear()

        assert len(roster.get_agents()) == 0

    def test_roster_persistence(self, test_data_dir, test_user_a):
        """Test that roster persists across instances."""
        # Create first roster instance and add agents
        roster1 = AgentRoster(test_data_dir, test_user_a["id"])
        roster1.add_agent("persistent_agent_1")
        roster1.add_agent("persistent_agent_2")

        # Create new roster instance and verify data persists
        roster2 = AgentRoster(test_data_dir, test_user_a["id"])
        agents = roster2.get_agents()

        assert len(agents) == 2
        assert "persistent_agent_1" in agents
        assert "persistent_agent_2" in agents

    def test_user_isolation_different_rosters(self, test_data_dir, test_user_a, test_user_b):
        """Test that different users have separate rosters."""
        roster_a = AgentRoster(test_data_dir, test_user_a["id"])
        roster_b = AgentRoster(test_data_dir, test_user_b["id"])

        # User A adds agents
        roster_a.add_agent("agent_a1")
        roster_a.add_agent("agent_a2")

        # User B adds agents
        roster_b.add_agent("agent_b1")
        roster_b.add_agent("agent_b2")

        # Verify rosters are separate
        agents_a = roster_a.get_agents()
        agents_b = roster_b.get_agents()

        assert len(agents_a) == 2
        assert len(agents_b) == 2
        assert "agent_a1" in agents_a
        assert "agent_a2" in agents_a
        assert "agent_b1" in agents_b
        assert "agent_b2" in agents_b

        # Cross-verify separation
        assert "agent_b1" not in agents_a
        assert "agent_a1" not in agents_b

    def test_user_isolation_clear_operation(self, test_data_dir, test_user_a, test_user_b):
        """Test that clear only affects the specific user's roster."""
        roster_a = AgentRoster(test_data_dir, test_user_a["id"])
        roster_b = AgentRoster(test_data_dir, test_user_b["id"])

        # Both users add agents
        roster_a.add_agent("agent_a")
        roster_b.add_agent("agent_b")

        # Clear user A's roster
        roster_a.clear()

        # Verify only user A's roster is cleared
        assert len(roster_a.get_agents()) == 0
        assert len(roster_b.get_agents()) == 1
        assert "agent_b" in roster_b.get_agents()

    def test_concurrent_add_operations(self, test_data_dir, test_user_a):
        """Test thread-safe concurrent add operations."""
        roster = AgentRoster(test_data_dir, test_user_a["id"])

        def add_agent(num):
            roster.add_agent(f"concurrent_agent_{num}")

        # Add 20 agents concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(add_agent, i) for i in range(20)]
            for future in futures:
                future.result()

        # Verify all agents were added
        agents = roster.get_agents()
        assert len(agents) == 20
        for i in range(20):
            assert f"concurrent_agent_{i}" in agents

    def test_concurrent_add_remove_operations(self, test_data_dir, test_user_a):
        """Test concurrent add and remove operations."""
        roster = AgentRoster(test_data_dir, test_user_a["id"])

        # Pre-populate with some agents
        for i in range(10):
            roster.add_agent(f"agent_{i}")

        def add_agent(num):
            roster.add_agent(f"new_agent_{num}")

        def remove_agent(num):
            roster.remove_agent(f"agent_{num}")

        # Perform concurrent adds and removes
        with ThreadPoolExecutor(max_workers=5) as executor:
            add_futures = [executor.submit(add_agent, i) for i in range(10)]
            remove_futures = [executor.submit(remove_agent, i) for i in range(5)]

            for future in add_futures + remove_futures:
                future.result()

        # Verify final state
        agents = roster.get_agents()
        # Should have: 5 remaining original + 10 new = 15
        assert len(agents) == 15

    def test_empty_roster_load(self, test_data_dir, test_user_a):
        """Test loading roster when no file exists."""
        roster = AgentRoster(test_data_dir, test_user_a["id"])

        # Should start empty
        agents = roster.get_agents()
        assert len(agents) == 0

    def test_roster_file_creation(self, test_data_dir, test_user_a):
        """Test that roster file is created on first save."""
        roster = AgentRoster(test_data_dir, test_user_a["id"])

        # Add agent to trigger save
        roster.add_agent("test_agent")

        # Verify file was created
        assert roster._user_roster_path.exists()

    def test_get_agent_roster_function(self, mock_settings, test_user_a):
        """Test get_agent_roster helper function."""
        roster = get_agent_roster(test_user_a["id"])

        roster.add_agent("test_agent")

        assert "test_agent" in roster.get_agents()
        assert roster._user_id == test_user_a["id"]

    def test_list_returns_copy(self, test_data_dir, test_user_a):
        """Test that list() returns a copy of the agents list."""
        roster = AgentRoster(test_data_dir, test_user_a["id"])

        roster.add_agent("agent_1")
        agents_list = roster.get_agents()

        # Modify the returned list
        agents_list.append("agent_2")

        # Verify original roster is unchanged
        assert len(roster.get_agents()) == 1
        assert "agent_2" not in roster.get_agents()

