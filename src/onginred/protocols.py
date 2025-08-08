"""Internal protocol definitions for type checking."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence
    from subprocess import CompletedProcess  # noqa: S404


class CommandRunner(Protocol):
    """Callable signature for running subprocess commands."""

    def __call__(self, args: Sequence[str], *, check: bool) -> CompletedProcess[str]:
        """Execute the given command and return the completed process."""
        ...
