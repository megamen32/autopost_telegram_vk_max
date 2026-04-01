class SyncError(Exception):
    pass


class AdapterNotFoundError(SyncError):
    pass


class RuleNotFoundError(SyncError):
    pass
