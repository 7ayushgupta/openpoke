"""Unit tests for TriggerService."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from server.services.triggers.service import TriggerService
from server.services.triggers.store import TriggerStore
from server.services.triggers import get_trigger_service


class TestTriggerService:
    """Test suite for TriggerService class."""

    @pytest.fixture
    def trigger_store(self, test_data_dir):
        """Create a trigger store for testing."""
        db_path = test_data_dir / "triggers.db"
        return TriggerStore(db_path)

    @pytest.fixture
    def trigger_service_a(self, trigger_store, test_user_a):
        """Create a trigger service for user A."""
        return TriggerService(trigger_store, test_user_a["id"])

    @pytest.fixture
    def trigger_service_b(self, trigger_store, test_user_b):
        """Create a trigger service for user B."""
        return TriggerService(trigger_store, test_user_b["id"])

    def test_create_trigger_service_with_user_id(self, trigger_store, test_user_a):
        """Test TriggerService creation with user_id."""
        service = TriggerService(trigger_store, test_user_a["id"])

        assert service._user_id == test_user_a["id"]
        assert service._store == trigger_store

    def test_create_simple_trigger(self, trigger_service_a):
        """Test creating a simple one-time trigger."""
        trigger = trigger_service_a.create_trigger(
            agent_name="test_agent",
            payload="Do something",
            start_time="2025-12-01T10:00:00"
        )

        assert trigger.agent_name == "test_agent"
        assert trigger.payload == "Do something"
        assert trigger.user_id == trigger_service_a._user_id
        assert trigger.status == "active"
        assert trigger.next_trigger is not None

    def test_create_recurring_trigger(self, trigger_service_a):
        """Test creating a recurring trigger."""
        trigger = trigger_service_a.create_trigger(
            agent_name="test_agent",
            payload="Daily task",
            recurrence_rule="FREQ=DAILY;INTERVAL=1",
            start_time="2025-12-01T09:00:00"
        )

        assert trigger.recurrence_rule is not None
        assert "FREQ=DAILY" in trigger.recurrence_rule
        assert trigger.next_trigger is not None

    def test_list_triggers_for_agent(self, trigger_service_a):
        """Test listing triggers for a specific agent."""
        # Create multiple triggers
        trigger_service_a.create_trigger(
            agent_name="agent_1",
            payload="Task 1",
            start_time="2025-12-01T10:00:00"
        )
        trigger_service_a.create_trigger(
            agent_name="agent_1",
            payload="Task 2",
            start_time="2025-12-01T11:00:00"
        )
        trigger_service_a.create_trigger(
            agent_name="agent_2",
            payload="Task 3",
            start_time="2025-12-01T12:00:00"
        )

        # List triggers for agent_1
        triggers = trigger_service_a.list_triggers(agent_name="agent_1")

        assert len(triggers) == 2
        assert all(t.agent_name == "agent_1" for t in triggers)

    def test_update_trigger_payload(self, trigger_service_a):
        """Test updating trigger payload."""
        trigger = trigger_service_a.create_trigger(
            agent_name="test_agent",
            payload="Original payload",
            start_time="2025-12-01T10:00:00"
        )

        updated = trigger_service_a.update_trigger(
            trigger_id=trigger.id,
            agent_name="test_agent",
            payload="Updated payload"
        )

        assert updated is not None
        assert updated.payload == "Updated payload"

    def test_update_trigger_status(self, trigger_service_a):
        """Test updating trigger status."""
        trigger = trigger_service_a.create_trigger(
            agent_name="test_agent",
            payload="Task",
            start_time="2025-12-01T10:00:00",
            status="active"
        )

        updated = trigger_service_a.update_trigger(
            trigger_id=trigger.id,
            agent_name="test_agent",
            status="paused"
        )

        assert updated is not None
        assert updated.status == "paused"

    def test_mark_as_completed(self, trigger_service_a):
        """Test marking trigger as completed."""
        trigger = trigger_service_a.create_trigger(
            agent_name="test_agent",
            payload="Task",
            start_time="2025-12-01T10:00:00"
        )

        trigger_service_a.mark_as_completed(
            trigger_id=trigger.id,
            agent_name="test_agent"
        )

        # Fetch updated trigger
        triggers = trigger_service_a.list_triggers(agent_name="test_agent")
        completed_trigger = next((t for t in triggers if t.id == trigger.id), None)

        assert completed_trigger is not None
        assert completed_trigger.status == "completed"
        assert completed_trigger.next_trigger is None

    def test_clear_all_triggers(self, trigger_service_a):
        """Test clearing all triggers for a user."""
        # Create triggers
        trigger_service_a.create_trigger(
            agent_name="agent_1",
            payload="Task 1",
            start_time="2025-12-01T10:00:00"
        )
        trigger_service_a.create_trigger(
            agent_name="agent_1",
            payload="Task 2",
            start_time="2025-12-01T11:00:00"
        )

        # Verify triggers exist
        assert len(trigger_service_a.list_triggers(agent_name="agent_1")) == 2

        # Clear all
        trigger_service_a.clear_all()

        # Verify triggers are cleared
        assert len(trigger_service_a.list_triggers(agent_name="agent_1")) == 0

    def test_user_isolation_create_triggers(self, trigger_service_a, trigger_service_b):
        """Test that different users can create independent triggers."""
        # User A creates trigger
        trigger_a = trigger_service_a.create_trigger(
            agent_name="my_agent",
            payload="User A's task",
            start_time="2025-12-01T10:00:00"
        )

        # User B creates trigger with same agent name
        trigger_b = trigger_service_b.create_trigger(
            agent_name="my_agent",
            payload="User B's task",
            start_time="2025-12-01T11:00:00"
        )

        # Verify triggers are separate
        assert trigger_a.user_id != trigger_b.user_id
        assert trigger_a.payload == "User A's task"
        assert trigger_b.payload == "User B's task"

    def test_user_isolation_list_triggers(self, trigger_service_a, trigger_service_b):
        """Test that users only see their own triggers."""
        # User A creates triggers
        trigger_service_a.create_trigger(
            agent_name="agent_1",
            payload="Task A1",
            start_time="2025-12-01T10:00:00"
        )
        trigger_service_a.create_trigger(
            agent_name="agent_1",
            payload="Task A2",
            start_time="2025-12-01T11:00:00"
        )

        # User B creates triggers
        trigger_service_b.create_trigger(
            agent_name="agent_1",
            payload="Task B1",
            start_time="2025-12-01T12:00:00"
        )

        # Verify each user only sees their own triggers
        triggers_a = trigger_service_a.list_triggers(agent_name="agent_1")
        triggers_b = trigger_service_b.list_triggers(agent_name="agent_1")

        assert len(triggers_a) == 2
        assert len(triggers_b) == 1
        assert all(t.user_id == trigger_service_a._user_id for t in triggers_a)
        assert all(t.user_id == trigger_service_b._user_id for t in triggers_b)

    def test_user_isolation_clear_operation(self, trigger_service_a, trigger_service_b):
        """Test that clear_all only affects the specific user."""
        # Both users create triggers
        trigger_service_a.create_trigger(
            agent_name="agent_1",
            payload="Task A",
            start_time="2025-12-01T10:00:00"
        )
        trigger_service_b.create_trigger(
            agent_name="agent_1",
            payload="Task B",
            start_time="2025-12-01T11:00:00"
        )

        # Clear user A's triggers
        trigger_service_a.clear_all()

        # Verify only user A's triggers are cleared
        triggers_a = trigger_service_a.list_triggers(agent_name="agent_1")
        triggers_b = trigger_service_b.list_triggers(agent_name="agent_1")

        assert len(triggers_a) == 0
        assert len(triggers_b) == 1

    def test_record_failure(self, trigger_service_a):
        """Test recording trigger failure."""
        trigger = trigger_service_a.create_trigger(
            agent_name="test_agent",
            payload="Task",
            start_time="2025-12-01T10:00:00"
        )

        trigger_service_a.record_failure(trigger, "Error message")

        # Fetch updated trigger
        triggers = trigger_service_a.list_triggers(agent_name="test_agent")
        updated_trigger = next((t for t in triggers if t.id == trigger.id), None)

        assert updated_trigger is not None
        assert updated_trigger.last_error == "Error message"

    def test_clear_next_fire(self, trigger_service_a):
        """Test clearing next fire time."""
        trigger = trigger_service_a.create_trigger(
            agent_name="test_agent",
            payload="Task",
            start_time="2025-12-01T10:00:00"
        )

        # Verify next_trigger is set
        assert trigger.next_trigger is not None

        # Clear next fire
        updated = trigger_service_a.clear_next_fire(
            trigger_id=trigger.id,
            agent_name="test_agent"
        )

        assert updated is not None
        assert updated.next_trigger is None

    def test_get_trigger_service_function(self, mock_settings, test_user_a):
        """Test get_trigger_service helper function."""
        service = get_trigger_service(test_user_a["id"])

        assert service._user_id == test_user_a["id"]

        # Verify it works
        trigger = service.create_trigger(
            agent_name="test_agent",
            payload="Test task",
            start_time="2025-12-01T10:00:00"
        )

        assert trigger.user_id == test_user_a["id"]

    def test_timezone_handling(self, trigger_service_a):
        """Test trigger creation with timezone."""
        trigger = trigger_service_a.create_trigger(
            agent_name="test_agent",
            payload="Task",
            start_time="2025-12-01T10:00:00",
            timezone_name="America/New_York"
        )

        assert trigger.timezone == "America/New_York"

    def test_create_trigger_with_inactive_status(self, trigger_service_a):
        """Test creating trigger with inactive status."""
        trigger = trigger_service_a.create_trigger(
            agent_name="test_agent",
            payload="Task",
            start_time="2025-12-01T10:00:00",
            status="paused"
        )

        assert trigger.status == "paused"

    def test_update_nonexistent_trigger(self, trigger_service_a):
        """Test updating non-existent trigger returns None."""
        updated = trigger_service_a.update_trigger(
            trigger_id=99999,
            agent_name="test_agent",
            payload="New payload"
        )

        assert updated is None

