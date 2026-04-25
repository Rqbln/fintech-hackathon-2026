"""Async retry wrapper for LLM calls — handles rate limits and asyncio conflicts.

GoogleGenAI._chat calls asyncio.run() internally (llama-index-llms-google-genai 0.9.x),
which raises RuntimeError when called from FastAPI's running event loop.
Fix: run it in asyncio.to_thread() — a thread pool has no active event loop,
so asyncio.run() works fine there.
"""

import asyncio
import structlog
from llama_index.core.llms import LLM, ChatMessage

log = structlog.get_logger()

_MAX_ATTEMPTS = 5
_BASE_DELAY = 4.0
_MAX_DELAY = 60.0


async def chat_with_retry(llm: LLM, messages: list[ChatMessage]):
    """Call the LLM with exponential backoff on rate-limit errors.

    Prefers achat() for true async LLMs. Falls back to running the sync
    chat() in a thread pool when achat() internally calls asyncio.run()
    (a known issue in llama-index-llms-google-genai ≤ 0.9.x).
    """
    delay = _BASE_DELAY
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            try:
                return await llm.achat(messages)
            except RuntimeError as exc:
                if "running event loop" in str(exc):
                    # LLM uses asyncio.run() internally — run sync version in thread
                    log.debug("llm_thread_fallback", attempt=attempt)
                    return await asyncio.to_thread(llm.chat, messages)
                raise
        except Exception as exc:
            msg = str(exc)
            is_rate_limit = (
                "429" in msg
                or "queue_exceeded" in msg
                or "too_many_requests" in msg
                or "rate limit" in msg.lower()
                or "resource_exhausted" in msg.lower()
            )
            if not is_rate_limit or attempt == _MAX_ATTEMPTS:
                raise
            log.warning("llm_rate_limit_retry", attempt=attempt, delay=delay, error=msg[:120])
            await asyncio.sleep(delay)
            delay = min(delay * 2, _MAX_DELAY)
