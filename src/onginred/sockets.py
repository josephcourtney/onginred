"""Socket configuration helpers and enums."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from onginred.cron import validate_range
from onginred.utils import to_camel

__all__ = [
    "SockFamily",
    "SockProtocol",
    "SockType",
    "SocketConfig",
]


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


class SocketConfig(BaseModel):
    """Model encapsulating socket-related launchd keys."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, alias_generator=to_camel)

    sock_type: SockType | None = Field(default=None, strict=True)
    passive: bool | None = Field(default=None, alias="SockPassive")
    node_name: str | None = Field(default=None, alias="SockNodeName")
    service_name: str | int | None = Field(default=None, alias="SockServiceName")
    family: SockFamily | None = Field(default=None, alias="SockFamily", strict=True)
    protocol: SockProtocol | None = Field(default=None, alias="SockProtocol", strict=True)
    path_name: str | None = Field(default=None, alias="SockPathName")
    secure_socket_key: str | None = Field(default=None, alias="SecureSocketWithKey")
    path_owner: int | None = Field(default=None, alias="SockPathOwner")
    path_group: int | None = Field(default=None, alias="SockPathGroup")
    path_mode: int | None = Field(default=None, alias="SockPathMode")
    bonjour: bool | str | list[str] | None = None
    multicast_group: str | None = None

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
