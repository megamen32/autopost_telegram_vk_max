from app.domain.enums import ContentType, Platform
from app.services.retry_policy import RetryPolicyService


def test_max_attachment_not_ready_is_retryable() -> None:
    svc = RetryPolicyService(base_delay_seconds=1, max_delay_seconds=10, jitter_seconds=0)
    decision = svc.decide(
        platform=Platform.MAX,
        media_types=[ContentType.VIDEO],
        error=RuntimeError("attachment.not.ready"),
        attempts=1,
        max_attempts=5,
    )
    assert decision.should_retry is True
    assert decision.error_code == "transient_error"


def test_vk_permission_denied_goes_dead_letter() -> None:
    svc = RetryPolicyService(base_delay_seconds=1, max_delay_seconds=10, jitter_seconds=0)
    decision = svc.decide(
        platform=Platform.VK,
        media_types=[ContentType.IMAGE],
        error=RuntimeError("permission to perform this action is denied"),
        attempts=1,
        max_attempts=5,
    )
    assert decision.should_retry is False
    assert decision.error_code == "non_retryable"


def test_telegram_max_attempts_stops_retrying() -> None:
    svc = RetryPolicyService(base_delay_seconds=1, max_delay_seconds=10, jitter_seconds=0)
    decision = svc.decide(
        platform=Platform.TELEGRAM,
        media_types=[ContentType.VIDEO],
        error=RuntimeError("timeout"),
        attempts=5,
        max_attempts=5,
    )
    assert decision.should_retry is False
    assert decision.error_code == "max_attempts_reached"
