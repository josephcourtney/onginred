from typing import cast

import pytest
from pydantic import ValidationError

from onginred.errors import InvalidSocketKeyError
from onginred.sockets import SockFamily, SockProtocol, SockType
from onginred.triggers import EventTriggers


def test_event_triggers_socket_and_mach():
    e = EventTriggers()
    e.add_socket("mysock", sock_type=SockType.STREAM, family=SockFamily.IPV4)
    e.add_mach_service("com.example.svc", reset_at_close=True, hide_until_checkin=True)
    d = e.to_plist_dict()
    assert "Sockets" in d
    assert "mysock" in d["Sockets"]
    mach = cast("dict", d["MachServices"])
    assert mach["com.example.svc"]["ResetAtClose"] is True


# Socket Configuration Tests
def test_socket_all_fields_set():
    e = EventTriggers()
    e.add_socket(
        "test_sock",
        sock_type=SockType.DGRAM,
        passive=True,
        node_name="localhost",
        service_name=8080,
        family=SockFamily.IPV4V6,
        protocol=SockProtocol.UDP,
        secure_socket_key="SECRET",
        path_owner=501,
        path_group=20,
        path_mode=0o755,
        bonjour=["myservice"],
        multicast_group="224.0.0.251",
    )
    sock_config = e.to_plist_dict()["Sockets"]["test_sock"]
    assert sock_config["SockType"] == "dgram"
    assert sock_config["SockFamily"] == "IPv4v6"
    assert sock_config["SockPathMode"] == 0o755


def test_socket_string_type_rejected():
    e = EventTriggers()
    with pytest.raises(ValidationError):
        e.add_socket("bad", sock_type="stream")  # type: ignore[arg-type]


def test_socket_conflicting_fields():
    e = EventTriggers()
    with pytest.raises(ValidationError):
        e.add_socket("bad", path_name="/tmp/sock", node_name="localhost")  # noqa: S108


def test_socket_conflicting_fields_service():
    e = EventTriggers()
    with pytest.raises(ValidationError):
        e.add_socket("bad", path_name="/tmp/sock", service_name=80)  # noqa: S108


# Invalid Socket Config
def test_invalid_socket_key_rejected():
    e = EventTriggers()
    # Improper manual dict insertion simulating malformed user input
    e.sockets["bad_socket"] = {"InvalidKey": "value"}
    with pytest.raises(InvalidSocketKeyError):
        _ = e.to_plist_dict()


@pytest.mark.parametrize("invalid_type", ["invalid", 123])
def test_socket_invalid_enum_values(invalid_type):
    e = EventTriggers()
    with pytest.raises(ValidationError):
        e.add_socket("bad_sock", sock_type=invalid_type)  # type: ignore[arg-type]


# Invalid Enum Value in Manual Socket Injection
def test_socket_config_manual_invalid_key():
    e = EventTriggers()
    e.sockets["bad"] = {"InvalidSockKey": True}
    with pytest.raises(InvalidSocketKeyError):
        _ = e.to_plist_dict()
