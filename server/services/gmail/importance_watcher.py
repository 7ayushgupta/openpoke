"""Background watcher that surfaces important Gmail emails proactively."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from .client import execute_gmail_tool
from .processing import EmailTextCleaner, ProcessedEmail, parse_gmail_fetch_response
from .seen_store import GmailSeenStore
from .importance_classifier import classify_email_importance
from ...logging_config import logger
from ...utils.timezones import convert_to_user_timezone


if TYPE_CHECKING:  # pragma: no cover - typing only
    from ...agents.interaction_agent.runtime import InteractionAgentRuntime


def _resolve_interaction_runtime(user_id: str) -> "InteractionAgentRuntime":
    from ...agents.interaction_agent.runtime import InteractionAgentRuntime

    return InteractionAgentRuntime(user_id)


DEFAULT_POLL_INTERVAL_SECONDS = 60.0
DEFAULT_LOOKBACK_MINUTES = 10
DEFAULT_MAX_RESULTS = 5
DEFAULT_SEEN_LIMIT = 300


_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


class ImportantEmailWatcher:
    """Poll Gmail for recent messages and surface important ones for a specific user."""

    def __init__(
        self,
        user_id: str,
        composio_user_id: str,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        lookback_minutes: int = DEFAULT_LOOKBACK_MINUTES,
        *,
        seen_store: Optional[GmailSeenStore] = None,
    ) -> None:
        self.user_id = user_id
        self.composio_user_id = composio_user_id
        self._poll_interval = poll_interval_seconds
        self._lookback_minutes = lookback_minutes
        self._lock = asyncio.Lock()
        self._task: Optional[asyncio.Task[None]] = None
        self._running = False
        
        # Create per-user seen store path
        user_seen_path = _DATA_DIR / "users" / user_id / "gmail_seen.json"
        self._seen_store = seen_store or GmailSeenStore(user_seen_path, DEFAULT_SEEN_LIMIT)
        self._cleaner = EmailTextCleaner(max_url_length=60)
        self._has_seeded_initial_snapshot = False
        self._last_poll_timestamp: Optional[datetime] = None

    # Start the background email polling task
    async def start(self) -> None:
        async with self._lock:
            if self._task and not self._task.done():
                return
            loop = asyncio.get_running_loop()
            self._running = True
            self._has_seeded_initial_snapshot = False
            self._last_poll_timestamp = None
            self._task = loop.create_task(self._run(), name=f"important-email-watcher-{self.user_id}")
            logger.info(
                f"Important email watcher started for user {self.user_id}",
                extra={
                    "user_id": self.user_id,
                    "interval_seconds": self._poll_interval,
                    "lookback_minutes": self._lookback_minutes
                },
            )

    # Stop the background email polling task gracefully
    async def stop(self) -> None:
        async with self._lock:
            self._running = False
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
                finally:
                    self._task = None
                logger.info(f"Important email watcher stopped for user {self.user_id}")

    async def _run(self) -> None:
        try:
            while self._running:
                try:
                    await self._poll_once()
                except Exception as exc:  # pragma: no cover - defensive
                    logger.exception(
                        f"Important email watcher poll failed for user {self.user_id}",
                        extra={"error": str(exc), "user_id": self.user_id}
                    )
                await asyncio.sleep(self._poll_interval)
        except asyncio.CancelledError:
            raise

    # Poll Gmail once for new messages and classify them for importance
    def _complete_poll(self, user_now: datetime) -> None:
        self._last_poll_timestamp = user_now
        self._has_seeded_initial_snapshot = True

    async def _poll_once(self) -> None:
        poll_started_at = datetime.now(timezone.utc)
        user_now = convert_to_user_timezone(poll_started_at)
        first_poll = not self._has_seeded_initial_snapshot
        previous_poll_timestamp = self._last_poll_timestamp
        interval_cutoff = user_now - timedelta(seconds=self._poll_interval)
        cutoff_time = interval_cutoff
        if previous_poll_timestamp is not None and previous_poll_timestamp > interval_cutoff:
            cutoff_time = previous_poll_timestamp

        # Use the stored composio_user_id for this user
        composio_user_id = self.composio_user_id
        
        query = f"label:INBOX newer_than:{self._lookback_minutes}m"
        arguments = {
            "query": query,
            "include_payload": True,
            "max_results": DEFAULT_MAX_RESULTS,
        }

        try:
            raw_result = execute_gmail_tool("GMAIL_FETCH_EMAILS", composio_user_id, arguments=arguments)
        except Exception as exc:
            logger.warning(
                "Failed to fetch Gmail messages for watcher",
                extra={"error": str(exc)},
            )
            return

        processed_emails, _ = parse_gmail_fetch_response(
            raw_result,
            query=query,
            cleaner=self._cleaner,
        )

        if not processed_emails:
            logger.debug("No recent Gmail messages found for watcher")
            self._complete_poll(user_now)
            return

        if first_poll:
            self._seen_store.mark_seen(email.id for email in processed_emails)
            logger.info(
                "Important email watcher completed initial warmup",
                extra={"skipped_ids": len(processed_emails)},
            )
            self._complete_poll(user_now)
            return

        unseen_emails: List[ProcessedEmail] = [
            email for email in processed_emails if not self._seen_store.is_seen(email.id)
        ]

        if not unseen_emails:
            logger.info(
                "Important email watcher check complete",
                extra={"emails_reviewed": 0, "surfaced": 0},
            )
            self._complete_poll(user_now)
            return

        unseen_emails.sort(key=lambda email: email.timestamp or datetime.now(timezone.utc))

        eligible_emails: List[ProcessedEmail] = []
        aged_emails: List[ProcessedEmail] = []

        for email in unseen_emails:
            email_timestamp = email.timestamp
            if email_timestamp.tzinfo is not None:
                email_timestamp = email_timestamp.astimezone(user_now.tzinfo)
            else:
                email_timestamp = email_timestamp.replace(tzinfo=user_now.tzinfo)

            if email_timestamp < cutoff_time:
                aged_emails.append(email)
                continue

            eligible_emails.append(email)

        if not eligible_emails and aged_emails:
            self._seen_store.mark_seen(email.id for email in aged_emails)
            logger.info(
                "Important email watcher check complete",
                extra={
                    "emails_reviewed": len(unseen_emails),
                    "surfaced": 0,
                    "suppressed_for_age": len(aged_emails),
                },
            )
            self._complete_poll(user_now)
            return

        summaries_sent = 0
        processed_ids: List[str] = [email.id for email in aged_emails]

        for email in eligible_emails:
            summary = await classify_email_importance(email)
            processed_ids.append(email.id)
            if not summary:
                continue

            summaries_sent += 1
            await self._dispatch_summary(summary)

        if processed_ids:
            self._seen_store.mark_seen(processed_ids)

        logger.info(
            "Important email watcher check complete",
            extra={
                "emails_reviewed": len(unseen_emails),
                "surfaced": summaries_sent,
                "suppressed_for_age": len(aged_emails),
            },
        )
        self._complete_poll(user_now)

    async def _dispatch_summary(self, summary: str) -> None:
        runtime = _resolve_interaction_runtime(self.user_id)
        try:
            contextualized = f"Important email watcher notification:\n{summary}"
            await runtime.handle_agent_message(contextualized)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(
                f"Failed to dispatch important email summary for user {self.user_id}",
                extra={"error": str(exc), "user_id": self.user_id},
            )


class MultiUserWatcherManager:
    """Manages per-user Gmail important email watchers."""
    
    REFRESH_INTERVAL_SECONDS = 300.0  # 5 minutes
    
    def __init__(self):
        self._watchers: Dict[str, ImportantEmailWatcher] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._refresh_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the manager and initial watchers."""
        async with self._lock:
            if self._running:
                logger.warning("MultiUserWatcherManager already running")
                return
            self._running = True

        logger.info("MultiUserWatcherManager starting")

        # Perform the initial refresh outside the lock so nested lock usage
        # inside _ensure_watcher_for_user does not deadlock on startup.
        try:
            await self._refresh_watchers()
        except Exception:
            # If refresh fails, mark the manager as not running and re-raise
            async with self._lock:
                self._running = False
            raise

        async with self._lock:
            try:
                loop = asyncio.get_running_loop()
                refresh_task = loop.create_task(self._refresh_loop(), name="watcher-manager-refresh")
            except RuntimeError:
                logger.error("No running event loop available for watcher manager")
                self._running = False
                return

            self._refresh_task = refresh_task
            logger.info("MultiUserWatcherManager started successfully")

    async def stop(self) -> None:
        """Stop all watchers and the manager."""
        async with self._lock:
            if not self._running:
                return
            
            self._running = False
            logger.info("MultiUserWatcherManager stopping")
            
            # Cancel refresh task
            if self._refresh_task:
                self._refresh_task.cancel()
                try:
                    await self._refresh_task
                except asyncio.CancelledError:
                    pass
                self._refresh_task = None
            
            # Stop all active watchers
            stop_tasks = []
            for user_id, watcher in self._watchers.items():
                logger.info(f"Stopping watcher for user {user_id}")
                stop_tasks.append(watcher.stop())
            
            if stop_tasks:
                await asyncio.gather(*stop_tasks, return_exceptions=True)
            
            self._watchers.clear()
            logger.info("MultiUserWatcherManager stopped")
    
    async def _refresh_loop(self) -> None:
        """Periodically refresh the list of watchers."""
        try:
            while self._running:
                await asyncio.sleep(self.REFRESH_INTERVAL_SECONDS)
                if self._running:
                    try:
                        await self._refresh_watchers()
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.exception("Failed to refresh watchers", extra={"error": str(exc)})
        except asyncio.CancelledError:
            raise
    
    async def _refresh_watchers(self) -> None:
        """Check for new/removed Gmail connections and update watchers."""
        from .client import get_all_connected_gmail_users
        
        try:
            connected_users = get_all_connected_gmail_users()
            logger.debug(f"Found {len(connected_users)} connected Gmail users")
            
            # Get current watcher user IDs
            current_user_ids = set(self._watchers.keys())
            new_user_ids = {user_id for user_id, _ in connected_users}
            
            # Add watchers for newly connected users
            for user_id, composio_user_id in connected_users:
                if user_id not in current_user_ids:
                    await self._ensure_watcher_for_user(user_id, composio_user_id)
            
            # Remove watchers for disconnected users
            disconnected_users = current_user_ids - new_user_ids
            for user_id in disconnected_users:
                await self._remove_watcher_for_user(user_id)
                
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Failed to refresh watcher list", extra={"error": str(exc)})
    
    async def _ensure_watcher_for_user(self, user_id: str, composio_user_id: str) -> None:
        """Create and start a watcher if it doesn't exist."""
        async with self._lock:
            if user_id in self._watchers:
                return
            
            try:
                logger.info(f"Creating Gmail watcher for user {user_id}")
                watcher = ImportantEmailWatcher(
                    user_id=user_id,
                    composio_user_id=composio_user_id
                )
                await watcher.start()
                self._watchers[user_id] = watcher
                logger.info(f"Gmail watcher created and started for user {user_id}")
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception(
                    f"Failed to create watcher for user {user_id}",
                    extra={"error": str(exc), "user_id": user_id}
                )
    
    async def _remove_watcher_for_user(self, user_id: str) -> None:
        """Stop and remove a watcher."""
        async with self._lock:
            watcher = self._watchers.pop(user_id, None)
            if watcher:
                try:
                    logger.info(f"Removing Gmail watcher for user {user_id}")
                    await watcher.stop()
                    logger.info(f"Gmail watcher removed for user {user_id}")
                except Exception as exc:  # pragma: no cover - defensive
                    logger.exception(
                        f"Failed to stop watcher for user {user_id}",
                        extra={"error": str(exc), "user_id": user_id}
                    )


_manager_instance: Optional[MultiUserWatcherManager] = None


def get_watcher_manager() -> MultiUserWatcherManager:
    """Get the global watcher manager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = MultiUserWatcherManager()
    return _manager_instance


# Legacy function kept for backwards compatibility
def get_important_email_watcher() -> ImportantEmailWatcher:
    """
    DEPRECATED: Use get_watcher_manager() instead.
    This function is kept for backwards compatibility but should not be used.
    """
    raise NotImplementedError(
        "get_important_email_watcher() is deprecated. "
        "Gmail watchers are now managed per-user via MultiUserWatcherManager. "
        "Use get_watcher_manager() instead."
    )


__all__ = ["ImportantEmailWatcher", "MultiUserWatcherManager", "get_watcher_manager", "get_important_email_watcher"]
