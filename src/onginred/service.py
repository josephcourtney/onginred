"""High level service management for launchd."""

from __future__ import annotations

import plistlib
import shutil
import subprocess  # noqa: S404
from pathlib import Path
from typing import TYPE_CHECKING

from .file_io import ensure_path

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from collections.abc import Callable, Sequence

    from .core import LaunchdSchedule

__all__ = ["LaunchdService", "LaunchdServiceError"]

DEFAULT_LOG_LOCATION = Path("/var/log/")
DEFAULT_INSTALL_LOCATION = Path.home() / "Library" / "LaunchAgents"


class LaunchdServiceError(Exception):
    pass


class LaunchdService:
    def __init__(
        self,
        bundle_identifier: str,
        command: Sequence[str] | None,
        schedule: LaunchdSchedule,
        *,
        plist_path: Path | str | None = None,
        log_name: str | None = None,
        log_dir: Path | None = None,
        stdout_log: Path | None = None,
        stderr_log: Path | None = None,
        launchctl_path: Path | None = None,
        program: str | None = None,
        runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
        create_dir: bool = False,
    ):
        if not program and not command:
            msg = "Missing required program or program arguments"
            raise TypeError(msg)
        self.bundle_identifier = bundle_identifier
        self.program = program

        if not command and not program:
            msg = "Missing required program or program arguments"
            raise TypeError(msg)

        self.command = list(command) if command else []
        self.schedule = schedule
        self.create_dir = create_dir
        self._runner = runner

        plist_filename = f"{bundle_identifier}.plist"
        self.plist_path = Path(plist_path) if plist_path else DEFAULT_INSTALL_LOCATION / plist_filename
        ensure_path(self.plist_path, allow_existing=True)

        self._ensure_log_files(
            log_name=log_name,
            log_dir=log_dir,
            stdout_log=stdout_log,
            stderr_log=stderr_log,
        )
        self.launchctl_path = launchctl_path or self._resolve_launchctl()

    def _ensure_log_files(
        self,
        log_name: str | None,
        log_dir: Path | None,
        stdout_log: Path | None,
        stderr_log: Path | None,
    ) -> None:
        log_name = log_name or self.bundle_identifier
        if log_dir and not (stdout_log or stderr_log):
            self.stdout_log = log_dir / f"{log_name}.out"
            self.stderr_log = log_dir / f"{log_name}.err"
        elif stdout_log:
            self.stdout_log = stdout_log
            self.stderr_log = stderr_log or stdout_log
        else:
            self.stdout_log = DEFAULT_LOG_LOCATION / f"{log_name}.out"
            self.stderr_log = DEFAULT_LOG_LOCATION / f"{log_name}.err"

        if self.create_dir:
            ensure_path(self.stdout_log)
            ensure_path(self.stderr_log)

    @staticmethod
    def _resolve_launchctl() -> Path | None:
        default = Path("/bin/launchctl")
        if default.exists():
            return default

        found = shutil.which("launchctl")
        if found:
            try:
                return Path(found).resolve(strict=True)
            except OSError as e:
                msg = "`launchctl` binary cannot be found at /bin/launchctl or via PATH."
                raise LaunchdServiceError(msg) from e
        msg = "`launchctl` binary cannot be found."
        raise LaunchdServiceError(msg)

    def install(self) -> None:
        plist = self.to_plist_dict()
        with self.plist_path.open("wb") as f:
            plistlib.dump(plist, f)
        res = self._runner([self.launchctl_path, "load", str(self.plist_path)], check=False)
        if res.returncode != 0:
            raise subprocess.CalledProcessError(res.returncode, res.args)

    def uninstall(self) -> None:
        self._runner([self.launchctl_path, "unload", str(self.plist_path)], check=True)
        self.plist_path.unlink(missing_ok=True)

    def to_plist_dict(self) -> dict:
        plist = {
            "Label": self.bundle_identifier,
            "StandardOutPath": str(self.stdout_log),
            "StandardErrorPath": str(self.stderr_log),
            **self.schedule.to_plist_dict(),
        }
        if self.program:
            plist["Program"] = self.program
            if self.command:
                plist["ProgramArguments"] = self.command
        else:
            plist["ProgramArguments"] = self.command
        return plist
