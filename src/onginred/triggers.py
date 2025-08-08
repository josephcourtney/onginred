"""Filesystem and time based launchd triggers."""

from __future__ import annotations

from datetime import time
from typing import Any, Final, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from onginred import cron
from onginred.errors import (
    DescriptorTypeError,
    InvalidSocketKeyError,
    InvalidTimeRangeError,
)
from onginred.sockets import SocketConfig, SockFamily, SockProtocol, SockType
from onginred.utils import to_camel

__all__ = ["FilesystemTriggers", "TimeTriggers"]


class TimeTriggers(BaseModel):
    model_config = ConfigDict(validate_assignment=True, populate_by_name=True, alias_generator=to_camel)

    calendar_entries: list[dict[str, int]] = Field(default_factory=list, alias="StartCalendarInterval")
    start_interval: int | None = Field(None, gt=0)

    class TimePlist(TypedDict, total=False):
        """Typed dictionary for serialized time trigger output."""

        StartCalendarInterval: list[dict[str, int]]
        StartInterval: int

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
            raise InvalidTimeRangeError(msg) from e

        for h, m in self._expand_range(start, end):
            self.add_calendar_entry(hour=h, minute=m)

    def set_start_interval(self, seconds: int) -> None:
        self.start_interval = seconds

    def to_plist_dict(self) -> TimePlist:
        data = self.model_dump(by_alias=True, exclude_none=True)
        if not data.get("StartCalendarInterval"):
            data.pop("StartCalendarInterval", None)
        return data  # type: ignore[return-value]

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
    model_config = ConfigDict(validate_assignment=True, populate_by_name=True, alias_generator=to_camel)

    watch_paths: set[str] = Field(default_factory=set)
    queue_directories: set[str] = Field(default_factory=set)
    start_on_mount: bool = False

    class FilesystemPlist(TypedDict, total=False):
        """Typed dictionary for serialized filesystem trigger output."""

        WatchPaths: list[str]
        QueueDirectories: list[str]
        StartOnMount: bool

    def add_watch_path(self, path: str) -> None:
        self.watch_paths.add(path)

    def add_queue_directory(self, path: str) -> None:
        self.queue_directories.add(path)

    def enable_start_on_mount(self) -> None:
        self.start_on_mount = True

    def to_plist_dict(self) -> FilesystemPlist:
        plist = self.model_dump(by_alias=True, exclude_defaults=True, exclude_none=True)
        if "WatchPaths" in plist:
            plist["WatchPaths"] = sorted(plist["WatchPaths"])
        if "QueueDirectories" in plist:
            plist["QueueDirectories"] = sorted(plist["QueueDirectories"])
        return plist  # type: ignore[return-value]


class EventTriggers(BaseModel):
    model_config = ConfigDict(validate_assignment=True, populate_by_name=True, alias_generator=to_camel)

    launch_events: dict[str, dict[str, dict]] = Field(default_factory=dict)
    sockets: dict[str, dict] = Field(default_factory=dict)
    mach_services: dict[str, bool | dict] = Field(default_factory=dict)

    class EventPlist(TypedDict, total=False):
        """Typed dictionary for serialized event trigger output."""

        LaunchEvents: dict[str, dict[str, dict]]
        Sockets: dict[str, dict]
        MachServices: dict[str, bool | dict]

    def add_launch_event(self, subsystem: str, event_name: str, descriptor: dict) -> None:
        if not isinstance(descriptor, dict):
            msg = "descriptor must be a dict"
            raise DescriptorTypeError(msg)
        self.launch_events.setdefault(subsystem, {})[event_name] = descriptor

    def add_socket(
        self,
        name: str,
        *,
        sock_type: SockType | None = None,
        passive: bool | None = None,
        node_name: str | None = None,
        service_name: str | int | None = None,
        family: SockFamily | None = None,
        protocol: SockProtocol | None = None,
        path_name: str | None = None,
        secure_socket_key: str | None = None,
        path_owner: int | None = None,
        path_group: int | None = None,
        path_mode: int | None = None,
        bonjour: bool | str | list[str] | None = None,
        multicast_group: str | None = None,
    ) -> None:
        cfg = SocketConfig(
            sock_type=sock_type,
            passive=passive,
            node_name=node_name,
            service_name=service_name,
            family=family,
            protocol=protocol,
            path_name=path_name,
            secure_socket_key=secure_socket_key,
            path_owner=path_owner,
            path_group=path_group,
            path_mode=path_mode,
            bonjour=bonjour,
            multicast_group=multicast_group,
        )
        self.sockets[name] = cfg.as_dict()

    def add_mach_service(
        self,
        name: str,
        *,
        reset_at_close: bool = False,
        hide_until_checkin: bool = False,
    ) -> None:
        config: dict | bool = {}
        if reset_at_close:
            config["ResetAtClose"] = True
        if hide_until_checkin:
            config["HideUntilCheckIn"] = True
        self.mach_services[name] = config or True

    def to_plist_dict(self) -> EventPlist:
        plist: dict[str, Any] = {}
        if self.launch_events:
            plist["LaunchEvents"] = self.launch_events
        if self.sockets:
            allowed = {
                "SockType",
                "SockPassive",
                "SockNodeName",
                "SockServiceName",
                "SockFamily",
                "SockProtocol",
                "SockPathName",
                "SecureSocketWithKey",
                "SockPathOwner",
                "SockPathGroup",
                "SockPathMode",
                "Bonjour",
                "MulticastGroup",
            }
            for config in self.sockets.values():
                invalid = set(config) - allowed
                if invalid:
                    msg = f"Invalid socket keys: {invalid}"
                    raise InvalidSocketKeyError(msg)
            plist["Sockets"] = self.sockets
        if self.mach_services:
            plist["MachServices"] = self.mach_services
        return plist  # type: ignore[return-value]
