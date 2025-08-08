import subprocess
import sys
import time

import pytest

from onginred.schedule import LaunchdSchedule
from onginred.service import LaunchdService


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
