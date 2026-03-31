from __future__ import annotations

from datetime import datetime, timezone


def utc_now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def to_utc_datetime(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)
