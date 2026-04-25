"""Async retry wrapper for LLM calls — handles Cerebras 429 queue_exceeded."""

import asyncio
import structlog
from llama_index.core.llms import LLM, ChatMessage

log = structlog.get_logger()

_MAX_ATTEMPTS = 5
_BASE_DELAY = 4.0   # seconds
_MAX_DELAY = 60.0


async def chat_with_retry(llm: LLM, messages: list[ChatMessage]):
    """Call llm.achat() with exponential backoff on 429 / rate-limit errors."""
    delay = _BASE_DELAY
    last_exc = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return await llm.achat(messages)
        except Exception as exc:
            msg = str(exc)
            is_rate_limit = (
                "429" in msg
                or "queue_exceeded" in msg
                or "too_many_requests" in msg
                or "rate limit" in msg.lower()
            )
            if not is_rate_limit or attempt == _MAX_ATTEMPTS:
                raise
            log.warning(
                "llm_rate_limit_retry",
                attempt=attempt,
                delay=delay,
                error=msg[:120],
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, _MAX_DELAY)
    raise last_exc  # unreachable but satisfies type checkers
