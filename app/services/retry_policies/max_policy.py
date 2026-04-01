from app.services.retry_policies.base import BasePlatformRetryPolicy


class MaxRetryPolicy(BasePlatformRetryPolicy):
    retryable_tokens = (
        "attachment.not.ready",
        "not ready",
        "too many requests",
        "rate limit",
        "429",
        "502",
        "503",
        "504",
        "timeout",
        "temporarily unavailable",
        "internal server error",
        "upload",
    )
    non_retryable_tokens = (
        "unauthorized",
        "forbidden",
        "chat not found",
        "message.format.invalid",
        "attachment.unsupported",
    )
    media_only_tokens = (
        "video processing",
        "media processing",
        "attachment",
    )
