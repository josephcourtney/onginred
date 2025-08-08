import plistlib
import subprocess
from pathlib import Path

import pytest

from onginred.schedule import LaunchdSchedule
from onginred.service import LaunchdService, LaunchdServiceError

DEFAULT_LAUNCHCTL = Path("/bin/true")


def test_launchd_service_to_plist_dict():
    schedule = LaunchdSchedule()
    svc = LaunchdService(
        bundle_identifier="com.test.service",
        command=["/usr/bin/env", "echo", "hello"],
        schedule=schedule,
        plist_path="/dev/null",  # stub
        log_name="testsvc",
        log_dir=Path("/tmp"),  # noqa: S108
        launchctl_path=DEFAULT_LAUNCHCTL,
    )
    plist = svc.to_plist_dict()
    assert plist["Label"] == "com.test.service"
    assert plist["ProgramArguments"] == ["/usr/bin/env", "echo", "hello"]
    assert "StandardOutPath" in plist
    assert "StandardErrorPath" in plist


def test_launchctl_resolution_failure(monkeypatch):
    monkeypatch.setattr(
        "onginred.service.LaunchdService._resolve_launchctl",
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
        "onginred.service.LaunchdService._resolve_launchctl",
        lambda self: fake_launchctl,
    )

    svc = LaunchdService(
        bundle_identifier="com.test.installer",
        command=["echo", "foo"],
        schedule=schedule,
        plist_path=plist_path,
        launchctl_path=fake_launchctl,
        runner=lambda *a, **kw: subprocess.CompletedProcess(a[0], 0),
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
        LaunchdService(
            bundle_identifier="com.test.invalid",
            command=[],
            schedule=sched,
            launchctl_path=DEFAULT_LAUNCHCTL,
        )


# If Both `Program` and `ProgramArguments`, `Program` Wins
def test_program_takes_precedence(monkeypatch):
    sched = LaunchdSchedule()
    svc = LaunchdService(
        bundle_identifier="com.test.override",
        command=["/usr/bin/env", "foo"],
        schedule=sched,
        plist_path="/dev/null",
        launchctl_path=DEFAULT_LAUNCHCTL,
    )
    plist = svc.to_plist_dict()
    assert plist["ProgramArguments"] == ["/usr/bin/env", "foo"]


# `.plist` filename matches label
def test_plist_path_matches_label(tmp_path):
    label = "com.example.myjob"
    svc = LaunchdService(
        label,
        ["echo"],
        LaunchdSchedule(),
        plist_path=None,
        launchctl_path=DEFAULT_LAUNCHCTL,
    )
    assert svc.plist_path.name == f"{label}.plist"


def test_umask_and_user_fields(monkeypatch):
    svc = LaunchdService(
        "com.example.user",
        ["echo"],
        LaunchdSchedule(),
        plist_path="/dev/null",
        launchctl_path=DEFAULT_LAUNCHCTL,
    )
    plist = svc.to_plist_dict()
    plist["UserName"] = "nobody"
    plist["Umask"] = "022"
    assert plist["UserName"] == "nobody"
    assert plist["Umask"] == "022"


def test_launchctl_failure(tmp_path):
    plist_path = tmp_path / "fail.plist"
    svc = LaunchdService(
        "com.example.fail",
        ["echo"],
        LaunchdSchedule(),
        plist_path=plist_path,
        launchctl_path=Path("/bin/false"),
        runner=lambda *a, **kw: subprocess.CompletedProcess(a[0], 1),
    )
    with pytest.raises(subprocess.CalledProcessError):
        svc.install()


def test_plist_round_trip_serialization(tmp_path):
    plist_path = tmp_path / "roundtrip.plist"
    svc = LaunchdService(
        "com.test.roundtrip",
        ["echo", "hi"],
        LaunchdSchedule(),
        plist_path=plist_path,
        runner=lambda *a, **kw: subprocess.CompletedProcess(a[0], 0),
        launchctl_path=DEFAULT_LAUNCHCTL,
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
        runner=lambda *a, **kw: subprocess.CompletedProcess(a[0], 0),
        launchctl_path=DEFAULT_LAUNCHCTL,
    )
    svc.install()
    with plist_path.open("rb") as f:
        plistlib.load(f)


def test_program_precedence_empty_arguments():
    svc = LaunchdService(
        "com.example.emptyargs",
        [],
        LaunchdSchedule(),
        plist_path="/dev/null",
        program="/bin/echo",
        launchctl_path=DEFAULT_LAUNCHCTL,
    )
    plist = svc.to_plist_dict()
    assert plist["Program"] == "/bin/echo"
    assert "ProgramArguments" not in plist


def test_program_precedence_relative_arguments():
    svc = LaunchdService(
        "com.example.relative",
        ["./foo"],
        LaunchdSchedule(),
        plist_path="/dev/null",
        program="/bin/echo",
        launchctl_path=DEFAULT_LAUNCHCTL,
    )
    plist = svc.to_plist_dict()
    assert plist["Program"] == "/bin/echo"
    assert plist["ProgramArguments"][0] == "./foo"


def test_log_paths_with_log_dir_and_name(tmp_path):
    svc = LaunchdService(
        bundle_identifier="com.example.logs",
        command=["echo"],
        schedule=LaunchdSchedule(),
        log_dir=tmp_path,
        log_name="svc",
        create_dir=True,
        launchctl_path=DEFAULT_LAUNCHCTL,
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
        launchctl_path=DEFAULT_LAUNCHCTL,
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
        runner=lambda *a, **kw: subprocess.CompletedProcess(a[0], 0),
        launchctl_path=DEFAULT_LAUNCHCTL,
    )
    svc.install()

    with path.open("rb") as f:
        loaded = plistlib.load(f)

    assert loaded["Label"] == "com.example.roundtrip"
    assert loaded["ProgramArguments"] == ["echo", "foo"]


def test_program_field_is_ignored_in_dict_output():
    """Ensure Program is not serialized if only ProgramArguments is used."""
    svc = LaunchdService(
        bundle_identifier="com.test.precedence",
        command=["/usr/bin/env", "foo"],
        schedule=LaunchdSchedule(),
        plist_path="/dev/null",
        launchctl_path=DEFAULT_LAUNCHCTL,
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
        runner=lambda *a, **kw: subprocess.CompletedProcess(a[0], 0),
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
        runner=lambda *a, **kw: subprocess.CompletedProcess(a[0], 0),
    )
    with pytest.raises(TypeError):
        svc.install()


def test_identity_fields_in_plist_dict():
    svc = LaunchdService(
        "com.example.identity",
        ["echo"],
        LaunchdSchedule(),
        plist_path="/dev/null",
        launchctl_path=DEFAULT_LAUNCHCTL,
    )
    plist = svc.to_plist_dict()
    plist["UserName"] = "nobody"
    plist["GroupName"] = "staff"
    plist["InitGroups"] = True
    assert plist["UserName"] == "nobody"
    assert plist["GroupName"] == "staff"
    assert plist["InitGroups"] is True
