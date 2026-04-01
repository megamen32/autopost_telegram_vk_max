from __future__ import annotations

from app.domain.enums import ContentType, Platform
from app.services.retry_policies import MaxRetryPolicy, RetryDecision, TelegramRetryPolicy, VkRetryPolicy


class RetryPolicyService:
    def __init__(self, *, base_delay_seconds: int = 5, max_delay_seconds: int = 900, jitter_seconds: int = 3) -> None:
        common = {
            "base_delay_seconds": base_delay_seconds,
            "max_delay_seconds": max_delay_seconds,
            "jitter_seconds": jitter_seconds,
        }
        self._policies = {
            Platform.TELEGRAM: TelegramRetryPolicy(**common),
            Platform.VK: VkRetryPolicy(**common),
            Platform.MAX: MaxRetryPolicy(**common),
        }

    def decide(
        self,
        *,
        platform: Platform,
        media_types: list[ContentType],
        error: Exception,
        attempts: int,
        max_attempts: int,
    ) -> RetryDecision:
        policy = self._policies[platform]
        return policy.decide(media_types=media_types, error=error, attempts=attempts, max_attempts=max_attempts)

    def next_attempt_at(self, delay_seconds: int):
        return TelegramRetryPolicy.next_attempt_at(delay_seconds)
