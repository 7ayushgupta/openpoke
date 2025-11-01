from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING

from ....config import get_settings
from ....logging_config import logger
from ....llm_client import LLMError, request_chat_completion
from .prompt_builder import SummaryPrompt, build_summarization_prompt
from .state import LogEntry, SummaryState
from .working_memory_log import get_working_memory_log

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from ..log import ConversationLog


def _resolve_conversation_log(user_id: str) -> "ConversationLog":
    from ..log import get_conversation_log

    return get_conversation_log(user_id)


def _collect_entries(log) -> List[LogEntry]:
    entries: List[LogEntry] = []
    for index, (tag, timestamp, payload) in enumerate(log.iter_entries()):
        entries.append(LogEntry(tag=tag, payload=payload, index=index, timestamp=timestamp or None))
    return entries


async def _call_llm(prompt: SummaryPrompt, model: str, api_key: Optional[str]) -> str:
    """Call LLM provider for summarization with retry logic."""
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = await request_chat_completion(
                model=model,
                messages=prompt.messages,
                system=prompt.system_prompt,
                api_key=api_key,
            )
            choices = response.get("choices") or []
            if not choices:
                raise LLMError("LLM response missing choices")
            message = choices[0].get("message") or {}
            content = (message.get("content") or "").strip()
            if content:
                return content
            raise LLMError("LLM response missing content")
        except LLMError as exc:
            last_error = exc
            if attempt == 0:
                logger.warning(
                    "Conversation summarization attempt failed; retrying",
                    extra={"error": str(exc), "attempt": attempt + 1},
                )
                continue
            logger.error(
                "Conversation summarization failed",
                extra={"error": str(exc), "attempt": attempt + 1},
            )
            break
        except Exception as exc:  # pragma: no cover - defensive
            last_error = exc
            logger.error(
                "Conversation summarization unexpected failure",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            break
    if last_error:
        raise last_error
    raise LLMError("Conversation summarization failed")


async def summarize_conversation(user_id: str) -> bool:
    logger.debug(f"[SUMMARIZATION] Checking if summarization is needed for user {user_id}")
    settings = get_settings()
    if not settings.summarization_enabled:
        logger.debug("[SUMMARIZATION] Summarization is disabled in settings")
        return False

    conversation_log = _resolve_conversation_log(user_id)
    working_memory_log = get_working_memory_log(user_id)

    entries = _collect_entries(conversation_log)
    state = working_memory_log.load_summary_state()

    threshold = settings.conversation_summary_threshold
    tail_size = max(settings.conversation_summary_tail_size, 0)

    if threshold <= 0:
        logger.debug("[SUMMARIZATION] Threshold is <= 0, skipping")
        return False

    unsummarized_entries = [entry for entry in entries if entry.index > state.last_index]
    if len(unsummarized_entries) < threshold + tail_size:
        logger.debug(
            f"[SUMMARIZATION] Not enough unsummarized entries ({len(unsummarized_entries)} < {threshold + tail_size})"
        )
        return False

    batch = unsummarized_entries[:threshold]
    cutoff_index = batch[-1].index

    prompt = build_summarization_prompt(state.summary_text, batch)

    # Determine which API key to use based on configured provider
    from ....llm_client.client import _get_provider
    provider = _get_provider()
    api_key = settings.openai_api_key if provider == "openai" else settings.openrouter_api_key

    logger.info(
        "[SUMMARIZATION] Conversation summarization started",
        extra={
            "entries_total": len(entries),
            "unsummarized": len(unsummarized_entries),
            "batch_size": len(batch),
            "last_index_before": state.last_index,
            "cutoff_index": cutoff_index,
            "model": settings.summarizer_model,
            "provider": provider,
        },
    )

    try:
        summary_text = await _call_llm(prompt, settings.summarizer_model, api_key)
        summary_body = summary_text if summary_text else state.summary_text
    except Exception as exc:
        logger.error(
            "[SUMMARIZATION] Failed to generate summary",
            extra={
                "error": str(exc),
                "error_type": type(exc).__name__,
                "model": settings.summarizer_model,
                "provider": provider,
                "batch_size": len(batch),
            }
        )
        raise

    refreshed_entries = _collect_entries(conversation_log)
    remaining_entries = [entry for entry in refreshed_entries if entry.index > cutoff_index]

    new_state = SummaryState(
        summary_text=summary_body,
        last_index=cutoff_index,
        updated_at=datetime.now(timezone.utc),
        unsummarized_entries=remaining_entries,
    )

    working_memory_log.write_summary_state(new_state)

    logger.info(
        "[SUMMARIZATION] Conversation summarization completed successfully",
        extra={
            "last_index_after": new_state.last_index,
            "remaining_unsummarized": len(new_state.unsummarized_entries),
            "summary_length": len(summary_body),
        },
    )
    return True


__all__ = ["summarize_conversation"]
