"""Core orchestration objects tying triggers and behaviour together."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from onginred.behavior import LaunchBehavior
from onginred.sockets import SockFamily, SockProtocol, SockType
from onginred.triggers import EventTriggers, FilesystemTriggers, TimeTriggers
from onginred.utils import to_camel

__all__ = [
    "LaunchdSchedule",
    "SockFamily",
    "SockProtocol",
    "SockType",
]


class ScheduleDict(TypedDict, total=False):
    StartCalendarInterval: list[dict[str, int]]
    StartInterval: int
    WatchPaths: list[str]
    QueueDirectories: list[str]
    StartOnMount: bool
    LaunchEvents: dict[str, dict[str, dict]]
    Sockets: dict[str, dict]
    MachServices: dict[str, bool | dict]
    RunAtLoad: bool
    EnablePressuredExit: bool
    EnableTransactions: bool
    LaunchOnlyOnce: bool
    ExitTimeout: int
    ThrottleInterval: int
    KeepAlive: bool | dict


class LaunchdSchedule(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True, alias_generator=to_camel)

    time: TimeTriggers = Field(default_factory=TimeTriggers)
    fs: FilesystemTriggers = Field(default_factory=FilesystemTriggers, alias="Filesystem")
    events: EventTriggers = Field(default_factory=EventTriggers)
    behavior: LaunchBehavior = Field(default_factory=LaunchBehavior)

    def add_cron(self, expr: str) -> None:
        self.time.add_cron(expr)

    def add_fixed_time(self, hour: int, minute: int) -> None:
        self.time.add_fixed_time(hour, minute)

    def add_watch_path(self, path: str) -> None:
        self.fs.add_watch_path(path)

    def add_queue_directory(self, path: str) -> None:
        self.fs.add_queue_directory(path)

    def add_launch_event(self, subsystem: str, event_name: str, descriptor: dict) -> None:
        self.events.add_launch_event(subsystem, event_name, descriptor)

    def add_socket(self, name: str, **cfg: Any) -> None:
        self.events.add_socket(name, **cfg)

    def add_mach_service(self, name: str, **cfg: Any) -> None:
        self.events.add_mach_service(name, **cfg)

    def set_exit_timeout(self, seconds: int) -> None:
        self.behavior.exit_timeout = seconds

    def set_throttle_interval(self, seconds: int) -> None:
        self.behavior.throttle_interval = seconds

    def to_plist_dict(self) -> ScheduleDict:
        """Combine subcomponent plist fragments into a single dictionary."""
        out: ScheduleDict = {}
        out.update(self.time.to_plist_dict())
        out.update(self.fs.to_plist_dict())
        out.update(self.events.to_plist_dict())
        out.update(self.behavior.to_plist_dict())
        return out

    @classmethod
    def load_from_json(cls, path: Path | str) -> LaunchdSchedule:
        """Instantiate a schedule from a JSON configuration file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)
