import string
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from onginred.errors import InvalidSocketKeyError
from onginred.file_io import TargetType, ensure_path
from onginred.triggers import EventTriggers, TimeTriggers


@given(st.integers(0, 59), st.integers(0, 23))
def test_cron_expansion(minute: int, hour: int) -> None:
    expr = f"{minute} {hour} * * *"
    t = TimeTriggers()
    t.add_cron(expr)
    assert {"Minute": minute, "Hour": hour} in t.calendar_entries


@given(st.text(alphabet=st.sampled_from(string.ascii_letters), min_size=1, max_size=10))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_path_resolution(tmp_path: Path, name: str) -> None:
    p = ensure_path(name, default_directory=tmp_path, target_type=TargetType.FILE, allow_existing=True)
    assert p.is_absolute()
    assert p.parent == tmp_path


VALID_SOCKET_KEYS = {
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


@given(st.text(min_size=1).filter(lambda k: k not in VALID_SOCKET_KEYS))
def test_invalid_socket_key(key: str) -> None:
    e = EventTriggers()
    e.sockets["sock"] = {key: True}
    with pytest.raises(InvalidSocketKeyError):
        e.to_plist_dict()
