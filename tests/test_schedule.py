from pathlib import Path

import pytest

from onginred.schedule import LaunchdSchedule
from onginred.triggers import EventTriggers


def test_event_triggers_default_plist():
    assert EventTriggers().to_plist_dict() == {}


def test_launchd_schedule_setters():
    sched = LaunchdSchedule()
    sched.add_cron("0 12 * * 1")
    sched.add_watch_path("/tmp/watched")  # noqa: S108
    sched.set_exit_timeout(30)
    sched.set_throttle_interval(10)
    assert sched.behavior.exit_timeout == 30
    assert sched.fs.watch_paths == {"/tmp/watched"}  # noqa: S108


def test_launchd_schedule_default_plist():
    assert LaunchdSchedule().to_plist_dict() == {}


@pytest.fixture
def temp_plist_file(tmp_path: Path) -> Path:
    return tmp_path / "com.test.service.plist"


def test_keepalive_with_startinterval():
    sched = LaunchdSchedule()
    sched.time.set_start_interval(300)
    sched.behavior.keep_alive = True
    plist = sched.to_plist_dict()
    assert plist["StartInterval"] == 300
    assert plist["KeepAlive"] is True


def test_multiple_launch_events():
    e = EventTriggers()
    e.add_launch_event("com.apple.power", "BatteryLow", {"Type": "IOKit"})
    e.add_launch_event("com.apple.network", "WiFiDown", {"Type": "IOKit"})
    plist = e.to_plist_dict()
    assert "BatteryLow" in plist["LaunchEvents"]["com.apple.power"]
    assert "WiFiDown" in plist["LaunchEvents"]["com.apple.network"]


def test_invalid_launch_event_descriptor():
    e = EventTriggers()
    with pytest.raises(TypeError):
        e.add_launch_event("com.apple", "FooEvent", "not-a-dict")  # type: ignore[arg-type]
