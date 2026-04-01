from app.services.retry_policies.base import BasePlatformRetryPolicy


class TelegramRetryPolicy(BasePlatformRetryPolicy):
    retryable_tokens = (
        "timeout",
        "timed out",
        "floodwait",
        "flood wait",
        "retry later",
        "too many requests",
        "server disconnected",
        "connection reset",
        "rpc call fail",
        "internal server error",
        "worker busy",
    )
    non_retryable_tokens = (
        "chatadminrequired",
        "forbidden",
        "channel_private",
        "user is deactivated",
        "bot was kicked",
        "message too long",
    )
    media_only_tokens = (
        "file reference",
        "cdn",
        "media empty",
        "video conversion",
        "media processing",
        "file parts invalid",
    )
