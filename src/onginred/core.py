from __future__ import annotations

import plistlib
import shutil
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import time
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Final

from croniter import croniter
from jkit.file_io import ensure_path

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
class CalendarEntryBuilder:
    entries: list[dict[str, int]]

    def __init__(self) -> None:
        self.entries = []

    def add(self, *, minute=None, hour=None, day=None, weekday=None, month=None) -> None:
        entry: dict[str, int] = {}
        if minute is not None:
            self._validate("Minute", minute, 0, 59)
            entry["Minute"] = minute
        if hour is not None:
            self._validate("Hour", hour, 0, 23)
            entry["Hour"] = hour
        if day is not None:
            self._validate("Day", day, 1, 31)
            entry["Day"] = day
        if weekday is not None:
            self._validate("Weekday", weekday, 0, 7)
            entry["Weekday"] = weekday
        if month is not None:
            self._validate("Month", month, 1, 12)
            entry["Month"] = month
        self.entries.append(entry)

    @staticmethod
    def _validate(name: str, value: int, lo: int, hi: int) -> None:
        if not (lo <= value <= hi):
            msg = f"{name} must be in [{lo}, {hi}]"
            raise ValueError(msg)

    def as_list(self) -> list[dict[str, int]]:
        return self.entries


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


class SocketConfigBuilder:
    def __init__(self) -> None:
        self.config: dict = {}

    def set(
        self,
        *,
        sock_type=None,
        passive=None,
        node_name=None,
        service_name=None,
        family=None,
        protocol=None,
        path_name=None,
        secure_socket_key=None,
        path_owner=None,
        path_group=None,
        path_mode=None,
        bonjour=None,
        multicast_group=None,
    ) -> None:
        if sock_type:
            self.config["SockType"] = sock_type.value
        if passive is not None:
            self.config["SockPassive"] = passive
        if node_name:
            self.config["SockNodeName"] = node_name
        if service_name:
            self.config["SockServiceName"] = service_name
        if family:
            self.config["SockFamily"] = family.value
        if protocol:
            self.config["SockProtocol"] = protocol.value
        if path_name:
            self.config["SockPathName"] = path_name
        if secure_socket_key:
            self.config["SecureSocketWithKey"] = secure_socket_key
        if path_owner is not None:
            self.config["SockPathOwner"] = path_owner
        if path_group is not None:
            self.config["SockPathGroup"] = path_group
        if path_mode is not None:
            self.config["SockPathMode"] = path_mode
        if bonjour is not None:
            self.config["Bonjour"] = bonjour
        if multicast_group:
            self.config["MulticastGroup"] = multicast_group

    def as_dict(self) -> dict:
        return self.config


class KeepAliveBuilder:
    def __init__(
        self,
        keep_alive: bool | dict | None,
        path_state: dict[str, bool],
        other_jobs: dict[str, bool],
        crashed: bool | None,
        successful_exit: bool | None,
    ) -> None:
        self.keep_alive = keep_alive
        self.path_state = path_state
        self.other_jobs = other_jobs
        self.crashed = crashed
        self.successful_exit = successful_exit

    def build(self) -> bool | dict | None:
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


@dataclass
class LaunchdSchedule:
    # === Time-based triggers ===
    calendar_entries: set[frozenset] = field(default_factory=set)
    start_interval: int | None = None

    # === File system triggers ===
    watch_paths: set[str] = field(default_factory=set)
    queue_directories: set[str] = field(default_factory=set)
    start_on_mount: bool = False

    # === Event and socket triggers ===
    launch_events: dict[str, dict[str, dict]] = field(default_factory=dict)
    sockets: dict[str, dict] = field(default_factory=dict)

    # === Launch modifiers ===
    run_at_load: bool | None = None
    keep_alive: bool | dict | None = None
    enable_pressured_exit: bool | None = None
    enable_transactions: bool | None = None
    exit_timeout: int | None = None
    throttle_interval: int | None = None
    launch_only_once: bool | None = None

    mach_services: dict[str, bool | dict] = field(default_factory=dict)
    keepalive_path_state: dict[str, bool] = field(default_factory=dict)
    keepalive_other_jobs: dict[str, bool] = field(default_factory=dict)
    restart_on_crash: bool | None = None
    restart_on_success: bool | None = None

    # === Public API ===

    def add_calendar_entry(
        self,
        *,
        minute: int | None = None,
        hour: int | None = None,
        day: int | None = None,
        weekday: int | None = None,
        month: int | None = None,
    ) -> None:
        entry = {}
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
        self.calendar_entries.add(frozenset(entry.items()))

    def add_cron(self, expr: str) -> None:
        if not croniter.is_valid(expr):
            msg = f"Invalid cron expression: {expr}"
            raise ValueError(msg)
        minute_s, hour_s, day_s, month_s, weekday_s = expr.split()

        minutes = _parse_cron_field(minute_s, 0, 59)
        hours = _parse_cron_field(hour_s, 0, 23)
        days = _parse_cron_field(day_s, 1, 31)
        months = _parse_cron_field(month_s, 1, 12)
        weekdays = _parse_cron_field(weekday_s, 0, 7)

        use_weekday = bool(weekday_s != "*")
        for m in minutes:
            for h in hours:
                for mo in months:
                    if days and not use_weekday:
                        for d in days:
                            self.add_calendar_entry(minute=m, hour=h, day=d, month=mo)
                    if use_weekday:
                        for wd in weekdays:
                            self.add_calendar_entry(minute=m, hour=h, weekday=wd, month=mo)

    def add_fixed_time(self, hour: int, minute: int) -> None:
        validate_range("Hour", hour, 0, 23)
        validate_range("Minute", minute, 0, 59)
        self.add_calendar_entry(hour=hour, minute=minute)

    def add_fixed_times(self, pairs: Iterable[tuple[int, int]]) -> None:
        for h, m in pairs:
            self.add_fixed_time(h, m)

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

    def add_watch_path(self, path: str) -> None:
        self.watch_paths.add(path)

    def add_queue_directory(self, path: str) -> None:
        self.queue_directories.add(path)

    def enable_start_on_mount(self) -> None:
        self.start_on_mount = True

    def add_launch_event(self, subsystem: str, event_name: str, descriptor: dict) -> None:
        if subsystem not in self.launch_events:
            self.launch_events[subsystem] = {}
        self.launch_events[subsystem][event_name] = descriptor

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
        builder = SocketConfigBuilder()
        builder.set(
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
        self.sockets[name] = builder.as_dict()

    # === Launch behavior configuration ===

    def set_run_at_load(self, value: bool) -> None:
        self.run_at_load = value

    def set_keep_alive(self, value: bool | dict) -> None:
        self.keep_alive = value

    def set_enable_pressured_exit(self, value: bool) -> None:
        self.enable_pressured_exit = value

    def set_enable_transactions(self, value: bool) -> None:
        self.enable_transactions = value

    def set_exit_timeout(self, seconds: int) -> None:
        if seconds < 0:
            msg = "ExitTimeOut must be ≥ 0"
            raise ValueError(msg)
        self.exit_timeout = seconds

    def set_throttle_interval(self, seconds: int) -> None:
        if seconds < 0:
            msg = "ThrottleInterval must be ≥ 0"
            raise ValueError(msg)
        self.throttle_interval = seconds

    def set_launch_only_once(self, value: bool) -> None:
        self.launch_only_once = value

    # === Internal utilities ===

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

    @staticmethod
    def _extract_minutes(expr: str) -> list[int]:
        m0 = expr.split(maxsplit=1)[0]
        if m0.startswith("*/"):
            step = int(m0[2:])
            return list(range(0, 60, step))
        if "," in m0:
            return [int(m) for m in m0.split(",")]
        if m0 == "*":
            return list(range(60))
        return [int(m0)]

    def add_mach_service(
        self, name: str, *, reset_at_close: bool = False, hide_until_checkin: bool = False
    ) -> None:
        config = {}
        if reset_at_close:
            config["ResetAtClose"] = True
        if hide_until_checkin:
            config["HideUntilCheckIn"] = True
        self.mach_services[name] = config or True

    def set_keepalive_path_state(self, path: str, exists: bool = True) -> None:
        self.keepalive_path_state[path] = exists

    def set_keepalive_other_job(self, label: str, loaded: bool = True) -> None:
        self.keepalive_other_jobs[label] = loaded

    def set_restart_on_crash(self, value: bool) -> None:
        self.restart_on_crash = value

    def set_restart_on_success(self, value: bool) -> None:
        self.restart_on_success = value

    def to_plist_dict(self) -> dict:
        plist: dict = {}
        # Time triggers
        entries = self.calendar.as_list()
        if entries:
            plist["StartCalendarInterval"] = entries
        if self.start_interval is not None:
            plist["StartInterval"] = self.start_interval
        # File-system triggers
        if self.watch_paths:
            plist["WatchPaths"] = sorted(self.watch_paths)
        if self.queue_directories:
            plist["QueueDirectories"] = sorted(self.queue_directories)
        if self.start_on_mount:
            plist["StartOnMount"] = True
        # Events + Sockets
        if self.launch_events:
            plist["LaunchEvents"] = self.launch_events
        if self.sockets:
            plist["Sockets"] = self.sockets
        # Mach services
        if self.mach_services:
            plist["MachServices"] = self.mach_services
        # Launch behavior flags
        if self.run_at_load is not None:
            plist["RunAtLoad"] = self.run_at_load
        if self.enable_pressured_exit is not None:
            plist["EnablePressuredExit"] = self.enable_pressured_exit
        if self.enable_transactions is not None:
            plist["EnableTransactions"] = self.enable_transactions
        if self.exit_timeout is not None:
            plist["ExitTimeOut"] = self.exit_timeout
        if self.throttle_interval is not None:
            plist["ThrottleInterval"] = self.throttle_interval
        if self.launch_only_once is not None:
            plist["LaunchOnlyOnce"] = self.launch_only_once
        # Keep‑alive logic via builder
        kab = KeepAliveBuilder(
            self.keep_alive,
            self.keepalive_path_state,
            self.keepalive_other_jobs,
            self.restart_on_crash,
            self.restart_on_success,
        )
        ka = kab.build()
        if ka is not None:
            plist["KeepAlive"] = ka
        return plist


class LaunchdService:
    def __init__(
        self,
        bundle_identifier: str,
        command: Sequence[str],
        schedule: LaunchdSchedule,
        plist_path: Path | str | None = None,
        log_name: str | None = None,
        log_dir: Path | None = None,
        stdout_log: Path | None = None,
        stderr_log: Path | None = None,
        launchctl_path: Path | None = None,
        *,
        create_dir: bool = False,
    ):
        self.bundle_identifier = bundle_identifier
        self.command = list(command)
        self.schedule = schedule
        self.create_dir = create_dir

        plist_filename = f"{bundle_identifier}.plist"
        self.plist_path = Path(plist_path) if plist_path else DEFAULT_INSTALL_LOCATION / plist_filename
        ensure_path(self.plist_path)

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

        ensure_path(self.stdout_log)
        ensure_path(self.stderr_log)

    def _resolve_launchctl(self) -> Path | None:
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
        return None

    def install(self) -> None:
        plist = self._generate_plist()
        with self.plist_path.open("wb") as f:
            plistlib.dump(plist, f)
        subprocess.run(["/bin/launchctl", "load", str(self.plist_path)], check=True)

    def uninstall(self) -> None:
        subprocess.run(["/bin/launchctl", "unload", str(self.plist_path)], check=True)
        self.plist_path.unlink(missing_ok=True)

    def _generate_plist(self) -> dict:
        # Start with the base configuration from the schedule
        plist = self.schedule.to_plist_dict()

        # Inject required metadata for launchd
        plist.update({
            "Label": self.bundle_identifier,
            "ProgramArguments": self.command,
            "StandardOutPath": str(self.stdout_log),
            "StandardErrorPath": str(self.stderr_log),
        })

        return plist
