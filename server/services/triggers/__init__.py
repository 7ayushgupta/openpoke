from __future__ import annotations

from pathlib import Path

from .models import TriggerRecord
from .service import TriggerService
from .store import TriggerStore


_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_default_db_path = _DATA_DIR / "triggers.db"
_trigger_store = TriggerStore(_default_db_path)


def get_trigger_service(user_id: str) -> TriggerService:
    """Get trigger service for a specific user."""
    return TriggerService(_trigger_store, user_id)


__all__ = [
    "TriggerRecord",
    "TriggerService",
    "get_trigger_service",
]
