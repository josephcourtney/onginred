from __future__ import annotations

import plistlib
import shutil
import subprocess  # noqa: S404
from collections.abc import Iterable
from datetime import time
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from croniter import croniter
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from onginred.file_io import ensure_path

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

# === Constants ===
DEFAULT_LOG_LOCATION = Path("/var/log/")
DEFAULT_INSTALL_LOCATION = Path.home() / "Library" / "LaunchAgents"


# === Exceptions ===
class LaunchdServiceError(Exception):
    pass


# === Enums ===
class SockType(StrEnum):
    STREAM = "stream"
    DGRAM = "dgram"
    SEQPACKET = "seqpacket"


class SockFamily(StrEnum):
    IPV4 = "IPv4"
    IPV6 = "IPv6"
    IPV4V6 = "IPv4v6"
    UNIX = "Unix"


class SockProtocol(StrEnum):
    TCP = "TCP"
    UDP = "UDP"


def validate_range(name: str, value: int, lo: int, hi: int) -> None:
    if not (lo <= value <= hi):
        msg = f"{name} must be in [{lo}, {hi}]"
        raise ValueError(msg)


# === Helpers ===
class KeepAliveConfig(BaseModel):
    keep_alive: bool | dict | None = None
    path_state: dict[str, bool] = Field(default_factory=dict)
    other_jobs: dict[str, bool] = Field(default_factory=dict)
    crashed: bool | None = None
    successful_exit: bool | None = None

    def build(self) -> bool | dict | None:
        if all([
            self.keep_alive is True,
            not self.path_state,
            not self.other_jobs,
            self.crashed is None,
            self.successful_exit is None,
        ]):
            return True
        if any([
            self.keep_alive,
            self.path_state,
            self.other_jobs,
            self.crashed is not None,
            self.successful_exit is not None,
        ]):
            base = self.keep_alive if isinstance(self.keep_alive, dict) else ({} if self.keep_alive else None)
            if base is None and self.keep_alive is True:
                return True
            if base is not None:
                if self.path_state:
                    base["PathState"] = self.path_state
                if self.other_jobs:
                    base["OtherJobEnabled"] = self.other_jobs
                if self.crashed is not None:
                    base["Crashed"] = self.crashed
                if self.successful_exit is not None:
                    base["SuccessfulExit"] = self.successful_exit
                return base
        return None


def _parse_cron_field(field: str, lo: int, hi: int) -> list[int]:
    if field == "*":
        return list(range(lo, hi + 1))
    values = set()
    for part in field.split(","):
        if "/" in part:
            base, step = part.split("/")
            step = int(step)
            base_range = _parse_cron_field(base, lo, hi)
            values.update(v for v in base_range if (v - lo) % step == 0)
        elif "-" in part:
            start, end = map(int, part.split("-"))
            values.update(range(start, end + 1))
        else:
            values.add(int(part))
    return sorted(values)


class SocketConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    sock_type: SockType | None = Field(default=None, alias="SockType")
    passive: bool | None = Field(default=None, alias="SockPassive")
    node_name: str | None = Field(default=None, alias="SockNodeName")
    service_name: str | int | None = Field(default=None, alias="SockServiceName")
    family: SockFamily | None = Field(default=None, alias="SockFamily")
    protocol: SockProtocol | None = Field(default=None, alias="SockProtocol")
    path_name: str | None = Field(default=None, alias="SockPathName")
    secure_socket_key: str | None = Field(default=None, alias="SecureSocketWithKey")
    path_owner: int | None = Field(default=None, alias="SockPathOwner")
    path_group: int | None = Field(default=None, alias="SockPathGroup")
    path_mode: int | None = Field(default=None, alias="SockPathMode")
    bonjour: bool | str | list[str] | None = Field(default=None, alias="Bonjour")
    multicast_group: str | None = Field(default=None, alias="MulticastGroup")

    @field_validator("path_mode")
    @classmethod
    def _valid_mode(cls, v: int | None) -> int | None:
        if v is not None:
            validate_range("SockPathMode", v, 0, 0o777)
        return v

    @model_validator(mode="after")
    def _check_conflicts(self) -> SocketConfig:
        if self.path_name and (self.node_name or self.service_name):
            msg = "SockPathName cannot be combined with SockNodeName or SockServiceName"
            raise ValueError(msg)
        return self

    def as_dict(self) -> dict:
        return self.model_dump(by_alias=True, exclude_none=True)


class TimeTriggers(BaseModel):
    model_config = ConfigDict(validate_assignment=True, populate_by_name=True)
    calendar_entries: list[dict[str, int]] = Field(default_factory=list, alias="StartCalendarInterval")
    start_interval: int | None = Field(None, alias="StartInterval")

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
            validate_range("Minute", minute, 0, 59)
            entry["Minute"] = minute
        if hour is not None:
            validate_range("Hour", hour, 0, 23)
            entry["Hour"] = hour
        if day is not None:
            validate_range("Day", day, 1, 31)
            entry["Day"] = day
        if weekday is not None:
            validate_range("Weekday", weekday, 0, 7)
            entry["Weekday"] = weekday
        if month is not None:
            validate_range("Month", month, 1, 12)
            entry["Month"] = month
        self.calendar_entries.append(entry)

    def add_fixed_time(self, hour: int, minute: int) -> None:
        validate_range("Hour", hour, 0, 23)
        validate_range("Minute", minute, 0, 59)
        self.add_calendar_entry(hour=hour, minute=minute)

    def add_fixed_times(self, pairs: Iterable[tuple[int, int]]) -> None:
        for h, m in pairs:
            self.add_fixed_time(h, m)

    def add_cron(self, expr: str) -> None:  # noqa: C901
        if not croniter.is_valid(expr):
            msg = f"Invalid cron expression: {expr}"
            raise ValueError(msg)
        minute_s, hour_s, day_s, month_s, weekday_s = expr.split()
        # simplify when day, month, weekday are wildcards
        if day_s == "*" and month_s == "*" and weekday_s == "*":
            minutes = _parse_cron_field(minute_s, 0, 59)
            hours = _parse_cron_field(hour_s, 0, 23)
            for m in minutes:
                for h in hours:
                    self.add_calendar_entry(minute=m, hour=h)
            return
        minutes = _parse_cron_field(minute_s, 0, 59)
        hours = _parse_cron_field(hour_s, 0, 23)
        days = _parse_cron_field(day_s, 1, 31)
        months = _parse_cron_field(month_s, 1, 12)
        weekdays = _parse_cron_field(weekday_s, 0, 7)
        use_weekday = weekday_s != "*"
        for m in minutes:
            for h in hours:
                for mo in months:
                    if not use_weekday:
                        for d in days:
                            self.add_calendar_entry(minute=m, hour=h, day=d, month=mo)
                    else:
                        for wd in weekdays:
                            self.add_calendar_entry(minute=m, hour=h, weekday=wd, month=mo)

    def add_suppression_window(self, spec: str) -> None:
        try:
            start_s, end_s = spec.split("-")
            start = self._parse_time(start_s)
            end = self._parse_time(end_s)
        except ValueError as e:
            msg = f"Invalid time range: {spec}"
            raise ValueError(msg) from e

        for m in self._expand_range(start, end):
            self.add_calendar_entry(minute=m)

    def set_start_interval(self, seconds: int) -> None:
        if seconds <= 0:
            msg = "StartInterval must be > 0"
            raise ValueError(msg)
        self.start_interval = seconds

    def to_plist_dict(self) -> dict[str, Any]:
        data = self.model_dump(by_alias=True, exclude_none=True)
        if not data.get("StartCalendarInterval"):
            data.pop("StartCalendarInterval", None)
        return data

    @staticmethod
    def _parse_time(s: str) -> time:
        hour, minute = map(int, s.split(":"))
        validate_range("Hour", hour, 0, 23)
        validate_range("Minute", minute, 0, 59)
        return time(hour, minute)

    @staticmethod
    def _expand_range(start: time, end: time) -> list[int]:
        def to_min(t: time) -> int:
            return t.hour * 60 + t.minute

        start_min = to_min(start)
        end_min = to_min(end)

        minutes: Final = list(range(1440))
        if end_min >= start_min:
            window = minutes[start_min : end_min + 1]
        else:
            window = minutes[start_min:] + minutes[: end_min + 1]

        return sorted({m % 60 for m in window})


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


class EventTriggers(BaseModel):
    model_config = ConfigDict(validate_assignment=True, populate_by_name=True)
    launch_events: dict[str, dict[str, dict]] = Field(default_factory=dict, alias="LaunchEvents")
    sockets: dict[str, dict] = Field(default_factory=dict, alias="Sockets")
    mach_services: dict[str, bool | dict] = Field(default_factory=dict, alias="MachServices")

    def add_launch_event(self, subsystem: str, event_name: str, descriptor: dict) -> None:
        if not isinstance(descriptor, dict):
            msg = "descriptor must be a dict"
            raise TypeError(msg)
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
        if sock_type is not None and not isinstance(sock_type, SockType):
            msg = f"Invalid SockType: {sock_type!r}"
            raise ValueError(msg)
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

    def to_plist_dict(self) -> dict[str, Any]:
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
                    raise KeyError(msg)
            plist["Sockets"] = self.sockets
        if self.mach_services:
            plist["MachServices"] = self.mach_services
        return plist


class LaunchBehavior(BaseModel):
    model_config = ConfigDict(validate_assignment=True, populate_by_name=True)
    run_at_load: bool | None = Field(None, alias="RunAtLoad")
    enable_pressured_exit: bool | None = Field(None, alias="EnablePressuredExit")
    enable_transactions: bool | None = Field(None, alias="EnableTransactions")
    launch_only_once: bool | None = Field(None, alias="LaunchOnlyOnce")
    exit_timeout: int | None = Field(None, alias="ExitTimeout", ge=0)
    throttle_interval: int | None = Field(None, alias="ThrottleInterval", ge=0)
    keep_alive: bool | dict | None = None
    path_state: dict[str, bool] = Field(default_factory=dict)
    other_jobs: dict[str, bool] = Field(default_factory=dict)
    crashed: bool | None = None
    successful_exit: bool | None = None

    def to_plist_dict(self) -> dict[str, Any]:
        plist = self.model_dump(
            by_alias=True,
            exclude_none=True,
            exclude={
                "keep_alive",
                "path_state",
                "other_jobs",
                "crashed",
                "successful_exit",
            },
        )
        kab = KeepAliveConfig(
            keep_alive=self.keep_alive,
            path_state=self.path_state,
            other_jobs=self.other_jobs,
            crashed=self.crashed,
            successful_exit=self.successful_exit,
        )
        ka = kab.build()
        if ka is not None:
            plist["KeepAlive"] = ka
        return plist


class LaunchdSchedule(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
    time: TimeTriggers = Field(default_factory=TimeTriggers)
    fs: FilesystemTriggers = Field(default_factory=FilesystemTriggers)
    events: EventTriggers = Field(default_factory=EventTriggers)
    behavior: LaunchBehavior = Field(default_factory=LaunchBehavior)

    def add_cron(self, expr: str) -> None:
        self.time.add_cron(expr)

    def add_watch_path(self, path: str) -> None:
        self.fs.add_watch_path(path)

    def set_exit_timeout(self, seconds: int) -> None:
        if seconds < 0:
            msg = "ExitTimeout must be ≥ 0"
            raise ValueError(msg)
        self.behavior.exit_timeout = seconds

    def set_throttle_interval(self, seconds: int) -> None:
        if seconds < 0:
            msg = "ThrottleInterval must be ≥ 0"
            raise ValueError(msg)
        self.behavior.throttle_interval = seconds

    def to_plist_dict(self) -> dict[str, Any]:
        out = {}
        out.update(self.time.to_plist_dict())
        out.update(self.fs.to_plist_dict())
        out.update(self.events.to_plist_dict())
        out.update(self.behavior.to_plist_dict())
        return out


class LaunchdService:
    def __init__(
        self,
        bundle_identifier: str,
        command: Sequence[str] | None,
        schedule: LaunchdSchedule,
        plist_path: Path | str | None = None,
        log_name: str | None = None,
        log_dir: Path | None = None,
        stdout_log: Path | None = None,
        stderr_log: Path | None = None,
        launchctl_path: Path | None = None,
        program: str | None = None,
        *,
        create_dir: bool = False,
    ):
        if not program and not command:
            msg = "Missing required program or program arguments"
            raise TypeError(msg)
        self.bundle_identifier = bundle_identifier
        self.program = program
        self.command = list(command) if command else []
        self.schedule = schedule
        self.create_dir = create_dir

        plist_filename = f"{bundle_identifier}.plist"
        self.plist_path = Path(plist_path) if plist_path else DEFAULT_INSTALL_LOCATION / plist_filename
        ensure_path(self.plist_path, allow_existing=True)

        self._ensure_log_files(
            log_name=log_name,
            log_dir=log_dir,
            stdout_log=stdout_log,
            stderr_log=stderr_log,
        )
        self.launchctl_path = launchctl_path or self._resolve_launchctl()

    def _ensure_log_files(
        self,
        log_name: str | None,
        log_dir: Path | None,
        stdout_log: Path | None,
        stderr_log: Path | None,
    ) -> None:
        log_name = log_name or self.bundle_identifier
        if log_dir and not (stdout_log or stderr_log):
            self.stdout_log = log_dir / f"{log_name}.out"
            self.stderr_log = log_dir / f"{log_name}.err"
        elif stdout_log:
            self.stdout_log = stdout_log
            self.stderr_log = stderr_log or stdout_log
        else:
            self.stdout_log = DEFAULT_LOG_LOCATION / f"{log_name}.out"
            self.stderr_log = DEFAULT_LOG_LOCATION / f"{log_name}.err"

        if self.create_dir:
            ensure_path(self.stdout_log)
            ensure_path(self.stderr_log)

    @staticmethod
    def _resolve_launchctl() -> Path | None:
        default = Path("/bin/launchctl")
        if default.exists():
            return default

        found = shutil.which("launchctl")
        if found:
            try:
                return Path(found).resolve(strict=True)
            except OSError as e:
                msg = "`launchctl` binary cannot be found at /bin/launchctl or via PATH."
                raise LaunchdServiceError(msg) from e
        else:
            msg = "`launchctl` binary cannot be found."
            raise LaunchdServiceError(msg)
        return None

    def install(self) -> None:
        plist = self.to_plist_dict()
        with self.plist_path.open("wb") as f:
            plistlib.dump(plist, f)
        res = subprocess.run([self.launchctl_path, "load", str(self.plist_path)], check=False)  # noqa: S603
        if res.returncode != 0:
            raise subprocess.CalledProcessError(res.returncode, res.args)

    def uninstall(self) -> None:
        subprocess.run([self.launchctl_path, "unload", str(self.plist_path)], check=True)  # noqa: S603
        self.plist_path.unlink(missing_ok=True)

    def to_plist_dict(self) -> dict:
        plist = {
            "Label": self.bundle_identifier,
            "StandardOutPath": str(self.stdout_log),
            "StandardErrorPath": str(self.stderr_log),
            **self.schedule.to_plist_dict(),
        }
        if self.program:
            plist["Program"] = self.program
            if self.command:
                plist["ProgramArguments"] = self.command
        else:
            plist["ProgramArguments"] = self.command
        return plist
