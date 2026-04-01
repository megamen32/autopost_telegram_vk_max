from app.services.retry_policies.base import BasePlatformRetryPolicy


class VkRetryPolicy(BasePlatformRetryPolicy):
    retryable_tokens = (
        "too many requests",
        "rate limit",
        "flood control",
        "internal server error",
        "temporarily unavailable",
        "timeout",
        "connection reset",
        "upload error",
        "server error",
        "error code 6",
        "error code 10",
    )
    non_retryable_tokens = (
        "access denied",
        "permission to perform this action is denied",
        "group authorization failed",
        "invalid access_token",
        "captcha needed",
    )
    media_only_tokens = (
        "photo save failed",
        "video is processing",
        "media processing",
        "attachment is invalid",
    )
