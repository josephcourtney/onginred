import pytest
from pydantic import ValidationError

from onginred.triggers import FilesystemTriggers, TimeTriggers


def test_time_triggers_add_fixed_time():
    t = TimeTriggers()
    t.add_fixed_time(2, 30)
    assert {"Hour": 2, "Minute": 30} in t.calendar_entries


def test_time_triggers_add_cron():
    t = TimeTriggers()
    t.add_cron("15 5 * * *")
    result = t.to_plist_dict()["StartCalendarInterval"]
    assert {"Hour": 5, "Minute": 15} in result


def test_time_triggers_invalid_cron():
    t = TimeTriggers()
    with pytest.raises(ValueError, match=r"."):
        t.add_cron("invalid cron expr")


def test_time_triggers_interval():
    t = TimeTriggers()
    t.set_start_interval(60)
    assert t.to_plist_dict()["StartInterval"] == 60


def test_time_triggers_invalid_interval():
    t = TimeTriggers()
    with pytest.raises(ValidationError):
        t.set_start_interval(0)


def test_time_triggers_default_plist():
    assert TimeTriggers().to_plist_dict() == {}


def test_suppression_window_adds_hours_and_minutes():
    t = TimeTriggers()
    t.add_suppression_window("23:58-00:01")
    entries = t.calendar_entries
    assert {"Hour": 23, "Minute": 58} in entries
    assert {"Hour": 0, "Minute": 1} in entries


# Error Handling: Invalid Input and System Errors
def test_invalid_cron_expression_rejected():
    t = TimeTriggers()
    with pytest.raises(ValueError, match=r"."):
        t.add_cron("bad cron expr")


def test_invalid_time_range_specifier():
    t = TimeTriggers()
    with pytest.raises(ValueError, match=r"."):
        t.add_suppression_window("25:00-26:00")


def test_suppression_window_midnight_wraparound():
    t = TimeTriggers()
    t.add_suppression_window("23:55-00:05")
    minutes = {entry["Minute"] for entry in t.calendar_entries if "Minute" in entry}
    assert 0 in minutes
    assert 59 in minutes or 60 not in minutes


def test_filesystem_triggers_default_plist():
    assert FilesystemTriggers().to_plist_dict() == {}


def test_filesystem_triggers():
    fs = FilesystemTriggers()
    fs.add_watch_path("/tmp/foo")  # noqa: S108
    fs.add_queue_directory("/tmp/bar")  # noqa: S108
    fs.enable_start_on_mount()
    d = fs.to_plist_dict()
    assert "/tmp/foo" in d["WatchPaths"]  # noqa: S108
    assert "/tmp/bar" in d["QueueDirectories"]  # noqa: S108
    assert d["StartOnMount"] is True
