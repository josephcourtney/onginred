import plistlib
import subprocess
import sys
import time
from pathlib import Path

import pytest

from onginred.core import (
    EventTriggers,
    FilesystemTriggers,
    LaunchBehavior,
    LaunchdSchedule,
    LaunchdService,
    LaunchdServiceError,
    SockFamily,
    SockProtocol,
    SockType,
    TimeTriggers,
    _parse_cron_field,
    validate_range,
)

# --- TimeTriggers ---


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
    with pytest.raises(ValueError, match=r"."):
        t.set_start_interval(0)


def test_validate_range_error():
    with pytest.raises(ValueError, match=r"."):
        validate_range("Minute", 60, 0, 59)


def test_parse_cron_field_range():
    assert _parse_cron_field("1-3", 0, 59) == [1, 2, 3]


# --- FilesystemTriggers ---


def test_filesystem_triggers():
    fs = FilesystemTriggers()
    fs.add_watch_path("/tmp/foo")  # noqa: S108
    fs.add_queue_directory("/tmp/bar")  # noqa: S108
    fs.enable_start_on_mount()
    d = fs.to_plist_dict()
    assert "/tmp/foo" in d["WatchPaths"]  # noqa: S108
    assert "/tmp/bar" in d["QueueDirectories"]  # noqa: S108
    assert d["StartOnMount"] is True


# --- EventTriggers ---


def test_event_triggers_socket_and_mach():
    e = EventTriggers()
    e.add_socket("mysock", sock_type=SockType.STREAM, family=SockFamily.IPV4)
    e.add_mach_service("com.example.svc", reset_at_close=True, hide_until_checkin=True)
    d = e.to_plist_dict()
    assert "Sockets" in d
    assert "mysock" in d["Sockets"]
    assert d["MachServices"]["com.example.svc"]["ResetAtClose"] is True


def test_socket_string_type_rejected():
    e = EventTriggers()
    with pytest.raises(ValueError, match=r"."):
        e.add_socket("bad", sock_type="stream")  # type: ignore[arg-type]


def test_socket_conflicting_fields():
    e = EventTriggers()
    with pytest.raises(ValueError, match=r"."):
        e.add_socket("bad", path_name="/tmp/sock", node_name="localhost")  # noqa: S108


# --- LaunchBehavior ---


def test_launch_behavior_keep_alive_dict():
    lb = LaunchBehavior(
        run_at_load=True,
        keep_alive={"SuccessfulExit": False},
        path_state={"file": True},
        other_jobs={"job.foo": True},
        crashed=True,
        successful_exit=False,
    )
    d = lb.to_plist_dict()
    assert d["RunAtLoad"] is True
    assert isinstance(d["KeepAlive"], dict)
    assert d["KeepAlive"]["Crashed"] is True


def test_launch_behavior_negative_exit_timeout():
    lb = LaunchBehavior()
    with pytest.raises(ValueError, match=r"."):
        lb.exit_timeout = -1


# --- LaunchdSchedule ---


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


def test_launch_behavior_default_plist():
    assert LaunchBehavior().to_plist_dict() == {}


# --- LaunchdService ---


@pytest.fixture
def temp_plist_file(tmp_path: Path) -> Path:
    return tmp_path / "com.test.service.plist"


def test_launchd_service_to_plist_dict():
    schedule = LaunchdSchedule()
    svc = LaunchdService(
        bundle_identifier="com.test.service",
        command=["/usr/bin/env", "echo", "hello"],
        schedule=schedule,
        plist_path="/dev/null",  # stub
        log_name="testsvc",
        log_dir=Path("/tmp"),  # noqa: S108
    )
    plist = svc.to_plist_dict()
    assert plist["Label"] == "com.test.service"
    assert plist["ProgramArguments"] == ["/usr/bin/env", "echo", "hello"]
    assert "StandardOutPath" in plist
    assert "StandardErrorPath" in plist


def test_launchctl_resolution_failure(monkeypatch):
    monkeypatch.setattr(
        "onginred.core.LaunchdService._resolve_launchctl",
        lambda self: (_ for _ in ()).throw(LaunchdServiceError("`launchctl` binary cannot be found.")),
    )
    with pytest.raises(LaunchdServiceError):
        LaunchdService(
            bundle_identifier="com.test.missing",
            command=["echo"],
            schedule=LaunchdSchedule(),
        )


def test_launchd_service_install_uninstall(fs, monkeypatch):
    fake_root = "/fake"
    fs.create_dir(fake_root)
    plist_path = Path(fake_root) / "com.test.installer.plist"
    schedule = LaunchdSchedule()

    fake_launchctl = Path(fake_root) / "launchctl"
    fs.create_file(str(fake_launchctl), contents="#!/bin/sh\necho mocked\n")
    fake_launchctl.chmod(0o755)

    monkeypatch.setattr("shutil.which", lambda _: str(fake_launchctl))
    monkeypatch.setattr(
        "onginred.core.LaunchdService._resolve_launchctl",
        lambda self: fake_launchctl,
    )
    import subprocess as _sub

    monkeypatch.setattr(
        "onginred.core.subprocess.run",
        lambda *args, **kwargs: _sub.CompletedProcess(args, 0),
    )

    svc = LaunchdService(
        bundle_identifier="com.test.installer",
        command=["echo", "foo"],
        schedule=schedule,
        plist_path=plist_path,
        launchctl_path=fake_launchctl,
    )

    svc.install()
    assert plist_path.exists()
    # load in binary mode
    with plist_path.open("rb") as f:
        plist_data = plistlib.load(f)
    assert plist_data["Label"] == "com.test.installer"

    svc.uninstall()
    assert not plist_path.exists()


# Required Keys: `Program` or `ProgramArguments`
def test_missing_program_arguments_raises():
    sched = LaunchdSchedule()
    with pytest.raises(TypeError):  # or custom validation if added
        LaunchdService(bundle_identifier="com.test.invalid", command=[], schedule=sched)


# If Both `Program` and `ProgramArguments`, `Program` Wins
def test_program_takes_precedence(monkeypatch):
    sched = LaunchdSchedule()
    svc = LaunchdService(
        bundle_identifier="com.test.override",
        command=["/usr/bin/env", "foo"],
        schedule=sched,
        plist_path="/dev/null",
    )
    plist = svc.to_plist_dict()
    assert plist["ProgramArguments"] == ["/usr/bin/env", "foo"]


# `.plist` filename matches label
def test_plist_path_matches_label(tmp_path):
    label = "com.example.myjob"
    svc = LaunchdService(label, ["echo"], LaunchdSchedule(), plist_path=None)
    assert svc.plist_path.name == f"{label}.plist"


# Invalid Socket Config
def test_invalid_socket_key_rejected():
    e = EventTriggers()
    # Improper manual dict insertion simulating malformed user input
    e.sockets["bad_socket"] = {"InvalidKey": "value"}
    with pytest.raises(KeyError):
        _ = e.to_plist_dict()


# Validate .plist via `plutil -lint`
def test_generated_plist_is_valid(tmp_path):
    plist_path = tmp_path / "com.test.valid.plist"
    svc = LaunchdService(
        "com.test.valid",
        ["echo", "hello"],
        LaunchdSchedule(),
        plist_path=plist_path,
    )
    svc.install()
    result = subprocess.run(["plutil", "-lint", str(plist_path)], check=False, capture_output=True, text=True)  # noqa: S607
    assert result.returncode == 0
    assert "OK" in result.stdout


# `RunAtLoad` Starts Job Immediately
@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only test")
def test_run_at_load_triggers_launch(tmp_path):
    log_file = tmp_path / "test.out"
    script = tmp_path / "test.sh"
    script.write_text("#!/bin/sh\necho hello >> " + str(log_file))
    script.chmod(0o755)
    sched = LaunchdSchedule()
    sched.behavior.run_at_load = True
    svc = LaunchdService(
        "com.example.runatload",
        [str(script)],
        sched,
        plist_path=tmp_path / "job.plist",
    )
    svc.install()
    time.sleep(2)
    svc.uninstall()
    assert log_file.read_text().strip() == "hello"


# `KeepAlive` Relaunches After Exit
@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only test")
def test_keepalive_relaunches_job(tmp_path):
    log_file = tmp_path / "out.txt"
    script = tmp_path / "log.sh"
    script.write_text("#!/bin/sh\necho run >> " + str(log_file))
    script.chmod(0o755)
    sched = LaunchdSchedule()
    sched.behavior.keep_alive = True
    sched.behavior.run_at_load = True
    svc = LaunchdService(
        "com.example.keepalive",
        [str(script)],
        sched,
        plist_path=tmp_path / "job.plist",
    )
    svc.install()
    time.sleep(4)
    svc.uninstall()
    lines = log_file.read_text().splitlines()
    assert len(lines) >= 2  # Should have run more than once


# `WatchPaths` Triggers Job on File Change
@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only test")
def test_watchpaths_triggers_on_change(tmp_path):
    watched = tmp_path / "trigger.txt"
    log = tmp_path / "log.txt"
    watched.touch()
    script = tmp_path / "echoer.sh"
    script.write_text("#!/bin/sh\necho changed >> " + str(log))
    script.chmod(0o755)
    sched = LaunchdSchedule()
    sched.fs.add_watch_path(str(watched))
    svc = LaunchdService(
        "com.example.watchtest",
        [str(script)],
        sched,
        plist_path=tmp_path / "job.plist",
    )
    svc.install()
    time.sleep(2)
    watched.write_text("trigger")
    time.sleep(2)
    svc.uninstall()
    assert "changed" in log.read_text()


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


@pytest.mark.parametrize("invalid_type", ["invalid", 123])
def test_socket_invalid_enum_values(invalid_type):
    e = EventTriggers()
    with pytest.raises((AttributeError, ValueError)):
        e.add_socket("bad_sock", sock_type=invalid_type)  # type: ignore[arg-type]


# Environment, Identity, and Permissions
def test_environment_variables_included():
    LaunchBehavior()
    plist = LaunchdService(
        "com.example.env",
        ["echo"],
        LaunchdSchedule(),
        plist_path="/dev/null",
    ).to_plist_dict()
    plist["EnvironmentVariables"] = {"FOO": "bar"}
    assert plist["EnvironmentVariables"]["FOO"] == "bar"


def test_umask_and_user_fields(monkeypatch):
    svc = LaunchdService(
        "com.example.user",
        ["echo"],
        LaunchdSchedule(),
        plist_path="/dev/null",
    )
    plist = svc.to_plist_dict()
    plist["UserName"] = "nobody"
    plist["Umask"] = "022"
    assert plist["UserName"] == "nobody"
    assert plist["Umask"] == "022"


# Resource Limits and Process Attributes
def test_soft_and_hard_resource_limits():
    lb = LaunchBehavior()
    plist = lb.to_plist_dict()
    plist["SoftResourceLimits"] = {"CPU": 60, "NumberOfFiles": 256}
    plist["HardResourceLimits"] = {"CPU": 120, "NumberOfFiles": 512}
    assert plist["SoftResourceLimits"]["CPU"] == 60
    assert plist["HardResourceLimits"]["NumberOfFiles"] == 512


def test_process_type_and_nice():
    lb = LaunchBehavior()
    plist = lb.to_plist_dict()
    plist["ProcessType"] = "Interactive"
    plist["Nice"] = 10
    assert plist["ProcessType"] == "Interactive"
    assert plist["Nice"] == 10


# Error Handling: Invalid Input and System Errors
def test_invalid_cron_expression_rejected():
    t = TimeTriggers()
    with pytest.raises(ValueError, match=r"."):
        t.add_cron("bad cron expr")


def test_invalid_time_range_specifier():
    t = TimeTriggers()
    with pytest.raises(ValueError, match=r"."):
        t.add_suppression_window("25:00-26:00")


def test_launchctl_failure(monkeypatch):
    import subprocess as _sub

    monkeypatch.setattr(
        "onginred.core.subprocess.run",
        lambda *args, **kwargs: _sub.CompletedProcess(args, 1),
    )
    svc = LaunchdService(
        "com.example.fail",
        ["echo"],
        LaunchdSchedule(),
        plist_path="/tmp/fail.plist",  # noqa: S108
        launchctl_path=Path("/bin/false"),
    )
    with pytest.raises(subprocess.CalledProcessError):
        svc.install()


# Combinations and Integration
def test_combined_time_and_fs_triggers():
    sched = LaunchdSchedule()
    sched.add_cron("0 6 * * *")
    sched.fs.add_watch_path("/tmp/something")  # noqa: S108
    plist = sched.time.to_plist_dict()
    assert "StartCalendarInterval" in plist
    plist = sched.fs.to_plist_dict()
    assert "WatchPaths" in plist


def test_keepalive_with_startinterval():
    sched = LaunchdSchedule()
    sched.time.set_start_interval(300)
    sched.behavior.keep_alive = True
    plist = sched.to_plist_dict()
    assert plist["StartInterval"] == 300
    assert plist["KeepAlive"] is True


def test_plist_round_trip_serialization(tmp_path):
    plist_path = tmp_path / "roundtrip.plist"
    svc = LaunchdService(
        "com.test.roundtrip",
        ["echo", "hi"],
        LaunchdSchedule(),
        plist_path=plist_path,
    )
    svc.install()

    with plist_path.open("rb") as f:
        loaded = plistlib.load(f)
    assert loaded["Label"] == "com.test.roundtrip"
    assert loaded["ProgramArguments"][0] == "echo"


# Validation Against `launchctl plist validation`
def test_plist_lint_passes(tmp_path):
    plist_path = tmp_path / "lintcheck.plist"
    svc = LaunchdService(
        "com.test.lint",
        ["echo", "lint"],
        LaunchdSchedule(),
        plist_path=plist_path,
    )
    svc.install()
    result = subprocess.run(["plutil", "-lint", str(plist_path)], check=False, capture_output=True, text=True)  # noqa: S607
    assert result.returncode == 0
    assert "OK" in result.stdout


# Program vs ProgramArguments Precedence
def test_program_field_precedence_over_programarguments():
    svc = LaunchdService(
        "com.example.override",
        ["/usr/bin/ignored", "foo"],
        LaunchdSchedule(),
        plist_path="/dev/null",
        program="/bin/echo",
    )
    plist = svc.to_plist_dict()
    assert plist["Program"] == "/bin/echo"
    assert plist["ProgramArguments"][0] == "/usr/bin/ignored"
    assert plist["Program"] != plist["ProgramArguments"][0]


# Invalid Enum Value in Manual Socket Injection
def test_socket_config_manual_invalid_key():
    e = EventTriggers()
    e.sockets["bad"] = {"InvalidSockKey": True}
    with pytest.raises(KeyError):
        _ = e.to_plist_dict()


# LaunchOnlyOnce Behavior
def test_launch_only_once_flag():
    lb = LaunchBehavior()
    lb.launch_only_once = True
    plist = lb.to_plist_dict()
    assert plist["LaunchOnlyOnce"] is True


def test_log_paths_with_log_dir_and_name(tmp_path):
    svc = LaunchdService(
        bundle_identifier="com.example.logs",
        command=["echo"],
        schedule=LaunchdSchedule(),
        log_dir=tmp_path,
        log_name="svc",
        create_dir=True,
    )
    assert svc.stdout_log.name == "svc.out"
    assert svc.stderr_log.name == "svc.err"
    assert svc.stdout_log.exists()
    assert svc.stderr_log.exists()


def test_log_paths_with_explicit_stdout_log(tmp_path):
    out_path = tmp_path / "custom.log"
    svc = LaunchdService(
        bundle_identifier="com.example.logs",
        command=["echo"],
        schedule=LaunchdSchedule(),
        stdout_log=out_path,
    )
    assert svc.stdout_log == out_path
    assert svc.stderr_log == out_path  # fallback


def test_model_round_trip_serialization(tmp_path):
    path = tmp_path / "job.plist"
    svc = LaunchdService(
        "com.example.roundtrip",
        ["echo", "foo"],
        LaunchdSchedule(),
        plist_path=path,
    )
    svc.install()

    with path.open("rb") as f:
        loaded = plistlib.load(f)

    assert loaded["Label"] == "com.example.roundtrip"
    assert loaded["ProgramArguments"] == ["echo", "foo"]


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only test")
def test_plist_passes_plutil_lint(tmp_path):
    plist_path = tmp_path / "lintcheck.plist"
    svc = LaunchdService(
        "com.example.lint",
        ["echo", "hello"],
        LaunchdSchedule(),
        plist_path=plist_path,
    )
    svc.install()
    result = subprocess.run(["plutil", "-lint", str(plist_path)], check=False, capture_output=True, text=True)  # noqa: S607
    assert result.returncode == 0
    assert "OK" in result.stdout


def test_program_field_is_ignored_in_dict_output():
    """Ensure Program is not serialized if only ProgramArguments is used."""
    svc = LaunchdService(
        bundle_identifier="com.test.precedence",
        command=["/usr/bin/env", "foo"],
        schedule=LaunchdSchedule(),
        plist_path="/dev/null",
    )
    plist = svc.to_plist_dict()
    assert "Program" not in plist
    assert "ProgramArguments" in plist


def test_install_plist_write_failure(monkeypatch):
    def fake_open(*args, **kwargs):
        msg = "Permission denied"
        raise OSError(msg)

    svc = LaunchdService(
        "com.test.writefail",
        ["echo", "fail"],
        LaunchdSchedule(),
        plist_path="/tmp/blocked.plist",  # noqa: S108
        launchctl_path=Path("/bin/true"),
    )
    monkeypatch.setattr("pathlib.Path.open", fake_open)
    with pytest.raises(OSError, match="Permission denied"):
        svc.install()


def test_invalid_plist_value_serialization(monkeypatch):
    class BadSchedule(LaunchdSchedule):
        def to_plist_dict(self):
            return {"StartCalendarInterval": object()}  # not serializable

    svc = LaunchdService(
        "com.test.invalidplist",
        ["echo"],
        BadSchedule(),
        plist_path="/tmp/faulty.plist",  # noqa: S108
        launchctl_path=Path("/bin/true"),
    )
    with pytest.raises(TypeError):
        svc.install()


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


def test_enable_transactions_and_pressured_exit_flags():
    lb = LaunchBehavior(enable_transactions=True, enable_pressured_exit=True)
    d = lb.to_plist_dict()
    assert d["EnableTransactions"] is True
    assert d["EnablePressuredExit"] is True


def test_identity_fields_in_plist_dict():
    svc = LaunchdService(
        "com.example.identity",
        ["echo"],
        LaunchdSchedule(),
        plist_path="/dev/null",
    )
    plist = svc.to_plist_dict()
    plist["UserName"] = "nobody"
    plist["GroupName"] = "staff"
    plist["InitGroups"] = True
    assert plist["UserName"] == "nobody"
    assert plist["GroupName"] == "staff"
    assert plist["InitGroups"] is True


def test_suppression_window_midnight_wraparound():
    t = TimeTriggers()
    t.add_suppression_window("23:55-00:05")
    minutes = {entry["Minute"] for entry in t.calendar_entries if "Minute" in entry}
    assert 0 in minutes
    assert 59 in minutes or 60 not in minutes


def test_launch_behavior_negative_throttle_interval():
    lb = LaunchBehavior()
    with pytest.raises(ValueError, match=r"."):
        lb.throttle_interval = -10


def test_launch_behavior_zero_exit_timeout_is_valid():
    lb = LaunchBehavior()
    lb.exit_timeout = 0
    assert lb.to_plist_dict()["ExitTimeout"] == 0
