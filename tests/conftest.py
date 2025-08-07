import plistlib
import subprocess
import threading
import time
from pathlib import Path

import pytest

_original_run = subprocess.run  # save real run


MAX_OUTPUT_LINES = 32


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Limit captured output per test."""
    # Only modify output for the call phase (i.e. test execution)
    if report.when == "call" and report.failed:
        new_sections: list[tuple[str, str]] = []
        for title, content in report.sections:
            if title.startswith(("Captured stdout", "Captured stderr")):
                lines = content.splitlines()
                if len(lines) > MAX_OUTPUT_LINES:
                    truncated_section: str = "\n".join([*lines[:MAX_OUTPUT_LINES], "... [output truncated]"])
                    new_sections.append((title, truncated_section))
                else:
                    new_sections.append((title, content))

            else:
                new_sections.append((title, content))
        report.sections = new_sections


def _handle_launchctl_load(cmd):
    """Simulate `launchctl load`: parse plist, then run job per its keys."""
    plist_path = Path(cmd[2])
    plist = plistlib.loads(plist_path.read_bytes())
    prog_args = plist.get("ProgramArguments", [])

    def run_job():
        _original_run(prog_args, check=True)

    # RunAtLoad
    if plist.get("RunAtLoad"):
        threading.Thread(target=run_job, daemon=True).start()

    # KeepAlive=True → second run ~1s later if RunAtLoad
    if plist.get("KeepAlive") is True and plist.get("RunAtLoad"):

        def delayed():
            time.sleep(1)
            run_job()

        threading.Thread(target=delayed, daemon=True).start()

    # WatchPaths → poll once for change
    paths = plist.get("WatchPaths", [])
    if paths:

        def watch():
            last = {p: Path(p).stat().st_mtime for p in paths}
            while True:
                time.sleep(0.5)
                for p in paths:
                    m = Path(p).stat().st_mtime
                    if m != last[p]:
                        run_job()
                        return

        threading.Thread(target=watch, daemon=True).start()

    return subprocess.CompletedProcess(cmd, 0)


def _handle_plutil_lint(cmd):
    """Simulate `plutil -lint`: always succeed with stdout "OK"."""
    name = Path(cmd[0]).name
    if name == "plutil" and len(cmd) > 1 and cmd[1] == "-lint":
        return subprocess.CompletedProcess(cmd, 0, stdout="OK\n")
    return None


def fake_run(cmd, *args, **kwargs):
    # Detect launchctl load/unload
    if len(cmd) >= 3 and cmd[1] == "load":
        return _handle_launchctl_load(cmd)
    if len(cmd) >= 3 and cmd[1] == "unload":
        return subprocess.CompletedProcess(cmd, 0)

    # Detect plutil -lint
    pl = _handle_plutil_lint(cmd)
    if pl is not None:
        return pl

    # Fallback to real run
    return _original_run(cmd, *args, **kwargs)


@pytest.fixture(autouse=True)
def fake_launchctl(monkeypatch):
    """Stub out subprocess.run globally to simulate launchctl and plutil."""
    monkeypatch.setattr(subprocess, "run", fake_run)
