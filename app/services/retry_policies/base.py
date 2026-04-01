from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.domain.enums import ContentType


@dataclass(slots=True)
class RetryDecision:
    should_retry: bool
    delay_seconds: int = 0
    reason: str | None = None
    error_code: str | None = None


class BasePlatformRetryPolicy:
    retryable_tokens: tuple[str, ...] = ()
    non_retryable_tokens: tuple[str, ...] = ()
    media_only_tokens: tuple[str, ...] = ()

    def __init__(self, *, base_delay_seconds: int, max_delay_seconds: int, jitter_seconds: int) -> None:
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.jitter_seconds = jitter_seconds

    def decide(self, *, media_types: list[ContentType], error: Exception, attempts: int, max_attempts: int) -> RetryDecision:
        if attempts >= max_attempts:
            return RetryDecision(False, reason="max_attempts_reached", error_code="max_attempts_reached")

        message = str(error).lower()
        if any(token in message for token in self.non_retryable_tokens):
            return RetryDecision(False, reason="non_retryable", error_code="non_retryable")

        retryable = any(token in message for token in self.retryable_tokens)
        if not retryable and media_types:
            retryable = any(token in message for token in self.media_only_tokens)

        if not retryable:
            return RetryDecision(False, reason="non_retryable", error_code="non_retryable")

        multiplier = 2 ** max(attempts - 1, 0)
        delay = min(self.base_delay_seconds * multiplier, self.max_delay_seconds)
        jitter = min(self.jitter_seconds, max(0, delay // 4))
        delay += jitter
        return RetryDecision(True, delay_seconds=delay, reason="transient_error", error_code="transient_error")

    @staticmethod
    def next_attempt_at(delay_seconds: int) -> datetime:
        return datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
