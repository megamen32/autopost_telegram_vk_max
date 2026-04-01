from app.domain.enums import ContentType, Platform
from app.services.retry_policy import RetryPolicyService


def test_retry_policy_retries_attachment_not_ready():
    service = RetryPolicyService(base_delay_seconds=5, max_delay_seconds=900, jitter_seconds=0)
    decision = service.decide(
        platform=Platform.MAX,
        media_types=[ContentType.VIDEO],
        error=RuntimeError("attachment.not.ready"),
        attempts=1,
        max_attempts=8,
    )
    assert decision.should_retry is True
    assert decision.delay_seconds == 5


def test_retry_policy_stops_on_non_retryable_error():
    service = RetryPolicyService()
    decision = service.decide(
        platform=Platform.VK,
        media_types=[ContentType.IMAGE],
        error=RuntimeError("permission denied"),
        attempts=1,
        max_attempts=8,
    )
    assert decision.should_retry is False
