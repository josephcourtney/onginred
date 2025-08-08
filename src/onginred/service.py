"""High level service management for launchd."""

from __future__ import annotations

import logging
import plistlib
import subprocess  # noqa: S404
from pathlib import Path
from typing import TYPE_CHECKING

from onginred.config import DEFAULT_INSTALL_LOCATION, DEFAULT_LOG_LOCATION
from onginred.file_io import ensure_path
from onginred.launchctl import LaunchctlClient

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from collections.abc import Sequence

    from onginred.schedule import LaunchdSchedule

__all__ = ["LaunchdService", "LaunchdServiceError"]


class LaunchdServiceError(Exception):
    """General service error."""


logger = logging.getLogger(__name__)


class LaunchdService:
    """Represents a launchd service and its associated plist file."""

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
        program: str | None = None,
        launchctl: LaunchctlClient | None = None,
        create_dir: bool = False,
    ):
        if not program and not command:
            msg = "Missing required program or program arguments"
            raise TypeError(msg)
        self.bundle_identifier = bundle_identifier
        self.program = program

        self.command = list(command) if command else []
        self.schedule = schedule
        self.create_dir = create_dir
        self.launchctl = launchctl or LaunchctlClient()

        plist_filename = f"{bundle_identifier}.plist"
        self.plist_path = Path(plist_path) if plist_path else DEFAULT_INSTALL_LOCATION / plist_filename
        ensure_path(self.plist_path, allow_existing=True)

        self._ensure_log_files(
            log_name=log_name,
            log_dir=log_dir,
            stdout_log=stdout_log,
            stderr_log=stderr_log,
        )

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

    def install(self) -> None:
        """Serialize the plist and load it via ``launchctl``."""
        plist = self.to_plist_dict()
        logger.info("serializing plist", extra={"path": str(self.plist_path)})
        with self.plist_path.open("wb") as f:
            plistlib.dump(plist, f)
        res = self.launchctl.load(self.plist_path)
        if res.returncode != 0:
            raise subprocess.CalledProcessError(res.returncode, res.args)

    def uninstall(self) -> None:
        """Unload the plist and remove the file."""
        self.launchctl.unload(self.plist_path)
        logger.info("removing plist", extra={"path": str(self.plist_path)})
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
