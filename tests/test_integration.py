import plistlib
import subprocess
from pathlib import Path
from typing import cast

from onginred.behavior import LaunchBehavior
from onginred.launchctl import LaunchctlClient
from onginred.schedule import LaunchdSchedule
from onginred.service import LaunchdService

DEFAULT_LAUNCHCTL = Path("/bin/true")


def make_client() -> LaunchctlClient:
    return LaunchctlClient(
        path=DEFAULT_LAUNCHCTL,
        runner=lambda args, *, check: subprocess.CompletedProcess(args, 0),
    )


# Validate .plist via `plutil -lint`
def test_generated_plist_is_valid(tmp_path):
    plist_path = tmp_path / "com.test.valid.plist"
    svc = LaunchdService(
        "com.test.valid",
        ["echo", "hello"],
        LaunchdSchedule(),
        plist_path=plist_path,
        launchctl=make_client(),
    )
    svc.install()
    with plist_path.open("rb") as f:
        plistlib.load(f)


# Combinations and Integration
def test_combined_time_and_fs_triggers():
    sched = LaunchdSchedule()
    sched.add_cron("0 6 * * *")
    sched.fs.add_watch_path("/tmp/something")  # noqa: S108
    plist = sched.time.to_plist_dict()
    assert "StartCalendarInterval" in plist
    plist = sched.fs.to_plist_dict()
    assert "WatchPaths" in plist


# Program vs ProgramArguments Precedence
def test_program_field_precedence_over_programarguments():
    svc = LaunchdService(
        "com.example.override",
        ["/usr/bin/ignored", "foo"],
        LaunchdSchedule(),
        plist_path="/dev/null",
        program="/bin/echo",
        launchctl=make_client(),
    )
    plist = svc.to_plist_dict()
    assert plist["Program"] == "/bin/echo"
    assert plist["ProgramArguments"][0] == "/usr/bin/ignored"
    assert plist["Program"] != plist["ProgramArguments"][0]


# Environment, Identity, and Permissions
def test_environment_variables_included():
    LaunchBehavior()
    plist = cast(
        "dict",
        LaunchdService(
            "com.example.env",
            ["echo"],
            LaunchdSchedule(),
            plist_path="/dev/null",
            launchctl=make_client(),
        ).to_plist_dict(),
    )
    plist["EnvironmentVariables"] = {"FOO": "bar"}
    assert plist["EnvironmentVariables"]["FOO"] == "bar"
