from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def _valid_utc_instants(local_time: datetime, timezone: ZoneInfo) -> set[datetime]:
    """Return UTC instants that round-trip to a possibly ambiguous local time."""
    instants: set[datetime] = set()
    for fold in (0, 1):
        candidate = local_time.replace(tzinfo=timezone, fold=fold)
        utc_candidate = candidate.astimezone(UTC)
        round_trip = utc_candidate.astimezone(timezone).replace(tzinfo=None)
        if round_trip == local_time:
            instants.add(utc_candidate)
    return instants


def _first_valid_instant(target_date: date, timezone: ZoneInfo) -> datetime:
    """Resolve local midnight, including gaps and skipped calendar dates."""
    local_time = datetime.combine(target_date, time.min)
    for minute in range(24 * 60 + 1):
        candidate = local_time + timedelta(minutes=minute)
        instants = _valid_utc_instants(candidate, timezone)
        if instants:
            return min(instants)
    raise ValueError("timezone has no valid instant within the target calendar day")


def calculate_next_review_at(
    reviewed_at: datetime,
    interval_days: int,
    timezone_name: str,
) -> datetime:
    """Convert an SM-2 interval into the next local-day boundary in UTC."""
    if reviewed_at.tzinfo is None or reviewed_at.utcoffset() is None:
        raise ValueError("reviewed_at must include a UTC offset")
    if (
        isinstance(interval_days, bool)
        or not isinstance(interval_days, int)
        or interval_days < 1
    ):
        raise ValueError("interval_days must be a positive integer")

    timezone = ZoneInfo(timezone_name)
    local_date = reviewed_at.astimezone(timezone).date()
    target_date = local_date + timedelta(days=interval_days)
    return _first_valid_instant(target_date, timezone)


def local_day_bounds(
    instant: datetime, timezone_name: str
) -> tuple[datetime, datetime]:
    """Return the half-open UTC interval for the instant's local calendar day."""
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("instant must include a UTC offset")
    timezone = ZoneInfo(timezone_name)
    local_date = instant.astimezone(timezone).date()
    return (
        _first_valid_instant(local_date, timezone),
        _first_valid_instant(local_date + timedelta(days=1), timezone),
    )


def local_date_range_bounds(
    date_from: date,
    date_to: date,
    timezone_name: str,
) -> tuple[datetime, datetime]:
    """Return UTC bounds for an inclusive range of local calendar dates."""
    if date_from > date_to:
        raise ValueError("date_from must not be after date_to")
    timezone = ZoneInfo(timezone_name)
    return (
        _first_valid_instant(date_from, timezone),
        _first_valid_instant(date_to + timedelta(days=1), timezone),
    )
