from __future__ import annotations

import asyncio
from typing import Dict

from ....logging_config import logger
from .summarizer import summarize_conversation

_pending_users: Dict[str, bool] = {}
_running_users: Dict[str, bool] = {}


def schedule_summarization(user_id: str) -> None:
    """Schedule a background summarization pass if not already queued."""
    global _pending_users
    _pending_users[user_id] = True
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.debug("summarization skipped (no running event loop)")
        return

    if not _running_users.get(user_id, False):
        loop.create_task(_run_worker(user_id))


async def _run_worker(user_id: str) -> None:
    global _pending_users, _running_users
    if _running_users.get(user_id, False):
        logger.debug(f"[SUMMARIZATION] Worker already running for user {user_id}, skipping")
        return

    logger.info(f"[SUMMARIZATION] Starting summarization worker for user {user_id}")
    _running_users[user_id] = True
    try:
        while _pending_users.get(user_id, False):
            _pending_users[user_id] = False
            logger.debug(f"[SUMMARIZATION] Processing pending summarization request for user {user_id}")
            try:
                await summarize_conversation(user_id)
            except Exception as exc:  # pragma: no cover - defensive
                import traceback
                logger.error(
                    f"[SUMMARIZATION] summarization worker failed for user {user_id}: {type(exc).__name__}: {str(exc)}",
                    extra={
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                        "user_id": user_id,
                    },
                )
                logger.debug(f"Traceback: {traceback.format_exc()}")
    finally:
        _running_users[user_id] = False
        logger.info(f"[SUMMARIZATION] Summarization worker stopped for user {user_id}")


__all__ = ["schedule_summarization"]
