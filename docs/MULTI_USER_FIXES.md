# Multi-User Support Fixes

## Overview
This document summarizes the fixes applied to ensure proper multi-user isolation and support across the OpenPoke codebase.

## Issues Fixed

### 1. Interaction Agent - Missing user_id Parameter
**Problem:** The `prepare_message_with_history()` function and `_render_active_agents()` were not accepting `user_id`, causing a `TypeError` when trying to fetch the agent roster.

**Files Modified:**
- `server/agents/interaction_agent/agent.py`
- `server/agents/interaction_agent/runtime.py`

**Changes:**
```python
# Before
def prepare_message_with_history(latest_text: str, transcript: str, message_type: str = "user"):
    ...

def _render_active_agents() -> str:
    roster = get_agent_roster()  # Missing user_id!
    ...

# After
def prepare_message_with_history(latest_text: str, transcript: str, user_id: str, message_type: str = "user"):
    ...

def _render_active_agents(user_id: str) -> str:
    roster = get_agent_roster(user_id)  # Now passing user_id
    ...
```

### 2. Summarization - Missing user_id Parameter
**Problem:** The summarization system was designed for single-user but the app is multi-user. Functions like `summarize_conversation()` and `schedule_summarization()` weren't accepting `user_id`.

**Files Modified:**
- `server/services/conversation/log.py`
- `server/services/conversation/summarization/scheduler.py`
- `server/services/conversation/summarization/summarizer.py`

**Changes:**
```python
# Before
def schedule_summarization() -> None:
    ...

async def summarize_conversation() -> bool:
    conversation_log = _resolve_conversation_log()  # Missing user_id!
    working_memory_log = get_working_memory_log()   # Missing user_id!
    ...

# After
def schedule_summarization(user_id: str) -> None:
    _pending_users[user_id] = True  # Track per user
    ...

async def summarize_conversation(user_id: str) -> bool:
    conversation_log = _resolve_conversation_log(user_id)
    working_memory_log = get_working_memory_log(user_id)
    ...
```

**Key Improvement:** Summarization workers are now tracked per-user, allowing multiple users to have concurrent summarization tasks without conflicts.

### 3. Enhanced Error Logging
**Problem:** Error messages were too generic (e.g., "Interaction agent failed") without showing the actual error details.

**Files Modified:**
- `server/agents/interaction_agent/runtime.py`
- `server/services/conversation/summarization/scheduler.py`
- `server/app.py`

**Changes:**
```python
# Before
logger.error("Interaction agent failed", extra={"error": str(exc)})

# After
logger.error(f"Interaction agent failed: {type(exc).__name__}: {str(exc)}", ...)
logger.debug(f"Traceback: {traceback.format_exc()}")
```

**Benefits:**
- Now shows the exact exception type and message
- Includes full stack trace in debug mode
- Makes debugging much easier

## Unit Tests Added

Created comprehensive unit tests in `tests/unit/test_interaction_agent_multi_user.py` covering:

### Test Coverage:
1. **Agent Rendering Tests**
   - `test_render_active_agents_requires_user_id` - Ensures user_id is required
   - `test_render_active_agents_single_agent` - Tests single agent rendering
   - `test_render_active_agents_multiple_agents` - Tests multiple agents
   - `test_render_active_agents_escapes_special_chars` - Tests XSS prevention
   - `test_render_active_agents_user_isolation` - Tests user data isolation

2. **Message Preparation Tests**
   - `test_prepare_message_with_history_requires_user_id` - Ensures user_id is required
   - `test_prepare_message_with_history_user_message` - Tests user message formatting
   - `test_prepare_message_with_history_agent_message` - Tests agent message formatting
   - `test_prepare_message_with_history_includes_active_agents` - Tests agent inclusion
   - `test_prepare_message_with_history_user_isolation` - Tests user data isolation

3. **Runtime Tests**
   - `test_runtime_initialization_with_user_id` - Tests proper initialization
   - `test_runtime_uses_user_specific_logs` - Tests log isolation

4. **Summarization Tests**
   - `test_schedule_summarization_requires_user_id` - Ensures user_id is required
   - `test_schedule_summarization_per_user` - Tests per-user tracking
   - `test_summarize_conversation_requires_user_id` - Tests conversation summarization

## User Isolation Guarantees

After these fixes, the following user isolation guarantees are enforced:

1. ✅ **Agent Rosters** - Each user has their own set of execution agents
2. ✅ **Conversation Logs** - Each user has their own conversation history
3. ✅ **Working Memory** - Each user has their own working memory/summary state
4. ✅ **Summarization Tasks** - Each user can have concurrent summarization without conflicts
5. ✅ **Interaction Context** - Messages prepared for the LLM only include user-specific agents

## Running the Tests

To verify the fixes:

```bash
# Run all unit tests
python3 -m pytest tests/unit/test_interaction_agent_multi_user.py -v

# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/unit/test_interaction_agent_multi_user.py --cov=server.agents.interaction_agent --cov-report=html
```

## Migration Notes

No database migrations or data changes are required. The fixes are backward compatible:
- Existing single-user data will continue to work
- Multi-user data is properly isolated by user_id in file paths
- No breaking API changes for external clients

## Verification Checklist

Before deploying:
- [x] All unit tests pass
- [x] No linter errors
- [x] Backward compatibility maintained
- [x] Error messages are informative
- [ ] Integration tests pass (run separately)
- [ ] Manual testing with multiple users

### 4. Execution Batch Manager Missing `user_id`
**Problem:** When execution agents completed and tried to dispatch results back to the interaction agent, they weren't passing `user_id` to create the `InteractionAgentRuntime`.

**Files Modified:**
- `server/agents/execution_agent/batch_manager.py`

**Changes:**
- Added `user_id` field to `PendingExecution` and `_BatchState` dataclasses
- Updated `_register_pending_execution()` to accept and store `user_id`
- Modified `_dispatch_to_interaction_agent()` to accept `user_id` parameter
- Now properly tracks which user each batch belongs to

### 5. Gmail Important Email Watcher - Temporary Disable
**Problem:** The Gmail importance watcher is a global background service that doesn't have user context, making it incompatible with multi-user architecture.

**Files Modified:**
- `server/services/gmail/importance_watcher.py`

**Changes:**
- Updated `_resolve_interaction_runtime()` to require `user_id` parameter
- Temporarily disabled email notification dispatching with a TODO comment
- Added warning log when notifications are skipped
- Marked for future refactoring to support per-user watchers

**Note:** This feature needs architectural changes to properly support multiple users. Each user should have their own watcher instance.

### 6. Frontend Authentication Token in Polling
**Problem:** The chat page was using direct `fetch()` calls without including the authentication token, causing 401 errors during message polling.

**Files Modified:**
- `web/app/page.tsx`

**Changes:**
- Changed from `fetch('/api/chat/history')` to `apiClient.getChatHistory()`
- Now properly includes `Authorization: Bearer <token>` header in all requests
- Consistent auth token usage across all API calls

## Related Issues

This fixes the following error patterns:
- `TypeError: get_agent_roster() missing 1 required positional argument: 'user_id'`
- `TypeError: get_conversation_log() missing 1 required positional argument: 'user_id'`
- `TypeError: InteractionAgentRuntime.__init__() missing 1 required positional argument: 'user_id'`
- `ERROR - Interaction agent failed` (now shows actual error)
- `ERROR - [SUMMARIZATION] summarization worker failed` (now shows actual error)
- `DEBUG - http error: 401 Authentication required` (fixed auth token in polling)

## Future Improvements

Consider these enhancements for production:

1. **Per-User Gmail Watchers** - Refactor Gmail watcher to support multiple users with separate polling
2. **Performance Monitoring** - Add metrics for per-user summarization performance
3. **Rate Limiting** - Add per-user rate limiting for API calls
4. **Resource Limits** - Add limits on number of agents per user
5. **Cleanup Jobs** - Add background jobs to clean up old user data
6. **Audit Logging** - Add audit logs for multi-user actions

## Contact

For questions or issues related to these fixes, please check the git commit history or open an issue.

