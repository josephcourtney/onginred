from __future__ import annotations

from onginred.schedule import LaunchdSchedule

__all__ = ["LaunchdBuilder"]


class LaunchdBuilder:
    """Fluent builder for :class:`LaunchdSchedule`."""

    def __init__(self, schedule: LaunchdSchedule | None = None) -> None:
        self.schedule = schedule or LaunchdSchedule()

    def cron(self, expr: str) -> LaunchdBuilder:
        self.schedule.add_cron(expr)
        return self

    def at(self, hour: int, minute: int) -> LaunchdBuilder:
        self.schedule.add_fixed_time(hour, minute)
        return self

    def watch(self, path: str) -> LaunchdBuilder:
        self.schedule.add_watch_path(path)
        return self

    def queue(self, path: str) -> LaunchdBuilder:
        self.schedule.add_queue_directory(path)
        return self

    def keep_alive(self) -> LaunchdBuilder:
        self.schedule.behavior.keep_alive = True
        return self

    def build(self) -> LaunchdSchedule:
        return self.schedule
