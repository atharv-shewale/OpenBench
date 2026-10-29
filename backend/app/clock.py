"""
Demo clock — all time-based logic must call app_now() instead of datetime.utcnow().

This allows the admin to fast-forward time during demos without waiting for real
time to pass. The offset is stored in a module-level integer.
"""
from datetime import datetime, timedelta, timezone

# Module-level demo offset in seconds (0 = real UTC)
_offset_seconds: int = 0


def app_now() -> datetime:
    """Return current UTC time + demo offset (timezone-naive, UTC)."""
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=_offset_seconds)


def advance_clock(seconds: int) -> int:
    """Add *seconds* to the demo offset. Returns the new total offset."""
    global _offset_seconds
    _offset_seconds += seconds
    return _offset_seconds


def reset_clock() -> int:
    """Reset the demo clock to real UTC. Returns 0."""
    global _offset_seconds
    _offset_seconds = 0
    return _offset_seconds


def get_offset() -> int:
    """Return the current demo offset in seconds."""
    return _offset_seconds

