"""Cron expression helpers."""

from __future__ import annotations

from croniter import croniter

__all__ = ["expand", "validate_range"]


def validate_range(name: str, value: int, lo: int, hi: int) -> None:
    """Ensure ``value`` falls within ``[lo, hi]``."""
    if not lo <= value <= hi:
        msg = f"{name} must be in [{lo}, {hi}]"
        raise ValueError(msg)


def _parse_cron_field(field: str, lo: int, hi: int) -> list[int]:
    """Expand a single cron field into a list of integers."""
    if field == "*":
        return list(range(lo, hi + 1))

    values: set[int] = set()
    for part in field.split(","):
        if "/" in part:
            base, step_s = part.split("/")
            try:
                step = int(step_s)
            except ValueError as e:  # pragma: no cover - defensive
                msg = f"Invalid cron field part: {part}"
                raise ValueError(msg) from e
            if step <= 0:
                msg = "step must be > 0"
                raise ValueError(msg)
            base_range = _parse_cron_field(base, lo, hi)
            values.update(v for v in base_range if (v - lo) % step == 0)
        elif "-" in part:
            start_s, end_s = part.split("-")
            try:
                start, end = int(start_s), int(end_s)
            except ValueError as e:  # pragma: no cover - defensive
                msg = f"Invalid cron field part: {part}"
                raise ValueError(msg) from e
            validate_range("cron range start", start, lo, hi)
            validate_range("cron range end", end, lo, hi)
            if start > end:
                msg = "start cannot exceed end"
                raise ValueError(msg)
            values.update(range(start, end + 1))
        else:
            try:
                val = int(part)
            except ValueError as e:  # pragma: no cover - defensive
                msg = f"Invalid cron field part: {part}"
                raise ValueError(msg) from e
            validate_range("cron value", val, lo, hi)
            values.add(val)

    return sorted(values)


def expand(expr: str) -> list[dict[str, int]]:
    """Expand a standard 5-field cron expression into launchd entries."""
    if not croniter.is_valid(expr):
        msg = f"Invalid cron expression: {expr}"
        raise ValueError(msg)

    minute_s, hour_s, day_s, month_s, weekday_s = expr.split()

    minutes = _parse_cron_field(minute_s, 0, 59)
    hours = _parse_cron_field(hour_s, 0, 23)
    days = _parse_cron_field(day_s, 1, 31)
    months = _parse_cron_field(month_s, 1, 12)
    weekdays = _parse_cron_field(weekday_s, 0, 7)

    entries: list[dict[str, int]] = []

    if day_s == "*" and month_s == "*" and weekday_s == "*":
        for m in minutes:
            entries.extend({"Minute": m, "Hour": h} for h in hours)
        return entries

    use_weekday = weekday_s != "*"
    for m in minutes:
        for h in hours:
            for mo in months:
                if not use_weekday:
                    entries.extend({"Minute": m, "Hour": h, "Day": d, "Month": mo} for d in days)
                else:
                    entries.extend({"Minute": m, "Hour": h, "Weekday": wd, "Month": mo} for wd in weekdays)

    return entries
