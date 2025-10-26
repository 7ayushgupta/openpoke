"""Admin status service to track interaction and execution agent statistics."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from ...logging_config import logger


@dataclass
class InteractionAgentStatus:
    """Status information for the interaction agent."""
    
    last_activity: Optional[datetime] = None
    total_messages_processed: int = 0
    
    @property
    def status(self) -> str:
        """Determine if interaction agent is active or idle."""
        if self.last_activity is None:
            return "idle"
        
        # Consider active if last activity within 30 seconds
        if datetime.now() - self.last_activity < timedelta(seconds=30):
            return "active"
        return "idle"


@dataclass
class ExecutionAgentStats:
    """Statistics for execution agents."""
    
    total_spawned: int = 0
    total_completed: int = 0
    total_failed: int = 0


class AdminStatusService:
    """Service to track and provide admin dashboard statistics."""
    
    def __init__(self):
        self._interaction_status = InteractionAgentStatus()
        self._execution_stats = ExecutionAgentStats()
        self._lock = None  # Will be set when threading is imported
    
    def _ensure_lock(self):
        """Lazy import and initialization of threading lock."""
        if self._lock is None:
            import threading
            self._lock = threading.Lock()
        return self._lock
    
    def record_interaction_activity(self) -> None:
        """Record that the interaction agent processed a message."""
        with self._ensure_lock():
            self._interaction_status.last_activity = datetime.now()
            self._interaction_status.total_messages_processed += 1
            logger.debug("Recorded interaction agent activity")
    
    def record_execution_agent_spawned(self) -> None:
        """Record that an execution agent was spawned."""
        with self._ensure_lock():
            self._execution_stats.total_spawned += 1
            logger.debug("Recorded execution agent spawned")
    
    def record_execution_agent_completed(self, success: bool) -> None:
        """Record that an execution agent completed (successfully or failed)."""
        with self._ensure_lock():
            if success:
                self._execution_stats.total_completed += 1
            else:
                self._execution_stats.total_failed += 1
            logger.debug(f"Recorded execution agent completion: success={success}")
    
    def get_interaction_agent_status(self) -> Dict:
        """Get current interaction agent status."""
        with self._ensure_lock():
            return {
                "status": self._interaction_status.status,
                "last_activity": self._interaction_status.last_activity.isoformat() if self._interaction_status.last_activity else None,
                "total_messages_processed": self._interaction_status.total_messages_processed
            }
    
    def get_execution_agent_statistics(self) -> Dict:
        """Get execution agent statistics."""
        with self._ensure_lock():
            return {
                "total_spawned": self._execution_stats.total_spawned,
                "total_completed": self._execution_stats.total_completed,
                "total_failed": self._execution_stats.total_failed
            }


# Singleton instance
_admin_status_service = AdminStatusService()


def get_admin_status_service() -> AdminStatusService:
    """Get the singleton admin status service."""
    return _admin_status_service
