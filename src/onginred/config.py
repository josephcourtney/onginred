"""Shared configuration constants for onginred."""

from __future__ import annotations

from pathlib import Path

# Default log output directory for launchd services
DEFAULT_LOG_LOCATION: Path = Path("/var/log/")

# Default install path for generated launchd property lists
DEFAULT_INSTALL_LOCATION: Path = Path.home() / "Library" / "LaunchAgents"

# Default location of the launchctl binary
DEFAULT_LAUNCHCTL_PATH: Path = Path("/bin/launchctl")
