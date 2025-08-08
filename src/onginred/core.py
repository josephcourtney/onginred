"""Core orchestration objects tying triggers and behaviour together."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .behavior import LaunchBehavior
from .sockets import SocketConfig, SockFamily, SockProtocol, SockType
from .triggers import FilesystemTriggers, TimeTriggers

__all__ = [
    "EventTriggers",
    "LaunchdSchedule",
    "SockFamily",
    "SockProtocol",
    "SockType",
]


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


class LaunchdSchedule(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    time: TimeTriggers = Field(default_factory=TimeTriggers, alias="Time")
    fs: FilesystemTriggers = Field(default_factory=FilesystemTriggers, alias="Filesystem")
    events: EventTriggers = Field(default_factory=EventTriggers, alias="Events")
    behavior: LaunchBehavior = Field(default_factory=LaunchBehavior, alias="Behavior")

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

    def to_plist_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        out.update(self.time.to_plist_dict())
        out.update(self.fs.to_plist_dict())
        out.update(self.events.to_plist_dict())
        out.update(self.behavior.to_plist_dict())
        return out
