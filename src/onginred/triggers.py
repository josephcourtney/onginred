"""Filesystem and time based launchd triggers."""

from __future__ import annotations

from datetime import time
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field

from . import cron

__all__ = ["FilesystemTriggers", "TimeTriggers"]


class TimeTriggers(BaseModel):
    model_config = ConfigDict(validate_assignment=True, populate_by_name=True)

    calendar_entries: list[dict[str, int]] = Field(default_factory=list, alias="StartCalendarInterval")
    start_interval: int | None = Field(None, alias="StartInterval", gt=0)

    def add_calendar_entry(
        self,
        *,
        minute: int | None = None,
        hour: int | None = None,
        day: int | None = None,
        weekday: int | None = None,
        month: int | None = None,
    ) -> None:
        entry: dict[str, int] = {}
        if minute is not None:
            cron.validate_range("Minute", minute, 0, 59)
            entry["Minute"] = minute
        if hour is not None:
            cron.validate_range("Hour", hour, 0, 23)
            entry["Hour"] = hour
        if day is not None:
            cron.validate_range("Day", day, 1, 31)
            entry["Day"] = day
        if weekday is not None:
            cron.validate_range("Weekday", weekday, 0, 7)
            entry["Weekday"] = weekday
        if month is not None:
            cron.validate_range("Month", month, 1, 12)
            entry["Month"] = month
        self.calendar_entries.append(entry)

    def add_fixed_time(self, hour: int, minute: int) -> None:
        cron.validate_range("Hour", hour, 0, 23)
        cron.validate_range("Minute", minute, 0, 59)
        self.add_calendar_entry(hour=hour, minute=minute)

    def add_fixed_times(self, pairs: list[tuple[int, int]] | tuple[tuple[int, int], ...]) -> None:
        for h, m in pairs:
            self.add_fixed_time(h, m)

    def add_cron(self, expr: str) -> None:
        self.calendar_entries.extend(cron.expand(expr))

    def add_suppression_window(self, spec: str) -> None:
        try:
            start_s, end_s = spec.split("-")
            start = self._parse_time(start_s)
            end = self._parse_time(end_s)
        except ValueError as e:
            msg = f"Invalid time range: {spec}"
            raise ValueError(msg) from e

        for h, m in self._expand_range(start, end):
            self.add_calendar_entry(hour=h, minute=m)

    def set_start_interval(self, seconds: int) -> None:
        self.start_interval = seconds

    def to_plist_dict(self) -> dict[str, Any]:
        data = self.model_dump(by_alias=True, exclude_none=True)
        if not data.get("StartCalendarInterval"):
            data.pop("StartCalendarInterval", None)
        return data

    @staticmethod
    def _parse_time(s: str) -> time:
        hour, minute = map(int, s.split(":"))
        cron.validate_range("Hour", hour, 0, 23)
        cron.validate_range("Minute", minute, 0, 59)
        return time(hour, minute)

    @staticmethod
    def _expand_range(start: time, end: time) -> list[tuple[int, int]]:
        def to_min(t: time) -> int:
            return t.hour * 60 + t.minute

        start_min = to_min(start)
        end_min = to_min(end)

        minutes: Final = list(range(1440))
        if end_min >= start_min:
            window = minutes[start_min : end_min + 1]
        else:
            window = minutes[start_min:] + minutes[: end_min + 1]

        return [divmod(m, 60) for m in window]


class FilesystemTriggers(BaseModel):
    model_config = ConfigDict(validate_assignment=True, populate_by_name=True)

    watch_paths: set[str] = Field(default_factory=set, alias="WatchPaths")
    queue_directories: set[str] = Field(default_factory=set, alias="QueueDirectories")
    start_on_mount: bool = Field(default=False, alias="StartOnMount")

    def add_watch_path(self, path: str) -> None:
        self.watch_paths.add(path)

    def add_queue_directory(self, path: str) -> None:
        self.queue_directories.add(path)

    def enable_start_on_mount(self) -> None:
        self.start_on_mount = True

    def to_plist_dict(self) -> dict[str, Any]:
        plist = self.model_dump(by_alias=True, exclude_defaults=True, exclude_none=True)
        if "WatchPaths" in plist:
            plist["WatchPaths"] = sorted(plist["WatchPaths"])
        if "QueueDirectories" in plist:
            plist["QueueDirectories"] = sorted(plist["QueueDirectories"])
        return plist
