from __future__ import annotations

import os
import platform
from enum import Enum
from os import PathLike
from pathlib import Path


class TargetType(Enum):
    FILE = "file"
    DIRECTORY = "directory"


def _is_posix() -> bool:
    return os.name == "posix"


def _set_posix_permissions(path: Path, mode: int) -> None:
    """Apply POSIX permissions to the given path."""
    if not _is_posix():
        msg = "Setting permissions is supported only on POSIX platforms."
        raise NotImplementedError(msg)
    try:
        path.chmod(mode)
    except OSError as e:
        msg = f"Failed to set permissions on {path}: {e}"
        raise OSError(msg) from e


def _validate_and_resolve_target(
    target: str | PathLike | None,
    default_directory: PathLike | None,
    *,
    resolve_symlinks: bool,
) -> Path:
    if not isinstance(target, (str, PathLike)):
        msg = f"Invalid target type: {type(target).__name__}. Must be str or Path."
        raise TypeError(msg)

    path = Path(target)

    if not path.is_absolute():
        if default_directory is None:
            msg = "Relative path provided but no default_directory specified."
            raise ValueError(msg)
        if not isinstance(default_directory, PathLike):
            msg = "default_directory must be a Path object."
            raise TypeError(msg)
        path = default_directory / path

    return path.resolve() if resolve_symlinks else path.absolute()


def _ensure_directory(path: Path, *, allow_existing: bool) -> None:
    try:
        path.mkdir(parents=True, exist_ok=allow_existing)
        if not path.is_dir():
            msg = f"Expected directory at {path}, but found a file."
            raise NotADirectoryError(msg)
    except FileExistsError as e:
        if not allow_existing:
            msg = f"Directory exists at {path} and allow_existing is False."
            raise FileExistsError(msg) from e
    except OSError as e:
        msg = f"Cannot create directory at {path}."
        raise OSError(msg) from e


def _ensure_file(path: Path, *, allow_existing: bool) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        msg = f"Failed to create parent directory {path.parent}: {e}"
        raise OSError(msg) from e

    if path.exists():
        if path.is_dir():
            msg = f"Expected file at {path}, but found a directory."
            raise IsADirectoryError(msg)
        if not allow_existing:
            msg = f"File exists at {path} and allow_existing is False."
            raise FileExistsError(msg)
        if not os.access(path, os.W_OK):
            msg = f"File exists at {path} but is not writable."
            raise OSError(msg)
    else:
        try:
            path.touch(exist_ok=False)
        except FileExistsError as e:
            if not allow_existing:
                msg = f"File {path} was created during check."
                raise FileExistsError(msg) from e
        except OSError as e:
            msg = f"Cannot create file at {path}: {e}"
            raise OSError(msg) from e


def ensure_path(
    target: str | PathLike,
    default_directory: PathLike | None = None,
    permissions: int | None = None,
    *,
    allow_existing: bool = False,
    target_type: TargetType | str = TargetType.FILE,
    resolve_symlinks: bool = True,
) -> Path:
    """Validate and prepare a writable path for file or directory output.

    This function ensures that the provided path exists (creating parent directories if needed),
    is of the correct type (file or directory), is writable, and optionally applies POSIX permissions.
    If the path is relative or a filename, it is resolved against a provided base directory.

    Args:
        target: Absolute or relative path to the file or directory.
        default_directory: Directory used to resolve relative paths or bare filenames. Required if `target`
            is not absolute.
        permissions: POSIX file permissions (e.g., 0o644) to apply if the path is created.
        allow_existing: Policy for dealing with existing filenames:
            - True: allow the path to exist and checks for writability
            - False: raise FileExistsError if the path already exists
        target_type: Either a `TargetType` enum (TargetType.FILE or TargetType.DIRECTORY), or the string
            "file" or "directory". Determines what kind of path to validate or create.
        resolve_symlinks: Policy for dealing with symlinks:
            - True: resolve symbolic links to their final destination.
            - False: preserve symlink components in the path.

    Returns
    -------
        An absolute, resolved Path object representing the file or directory.

    Raises
    ------
        ValueError: If `target` is None or if `target_type` is invalid.
        TypeError: If argument types are incorrect.
        FileExistsError: If `allow_existing` is False and the path exists.
        IsADirectoryError: If a file path points to a directory.
        NotADirectoryError: If a directory path points to a file.
        OSError: If the path or its parent directory cannot be created or written to.
        NotImplementedError: If permissions are set on a non-POSIX platform.

    Notes
    -----
        - If the path exists and `allow_existing=True`, it is validated for writability but not modified.
        - This function does not open, write, or truncate the file or directory contents.
        - On POSIX systems, permissions are applied only when the path is newly created.
    """
    path = _validate_and_resolve_target(target, default_directory, resolve_symlinks=resolve_symlinks)

    if permissions is not None and not isinstance(permissions, int):
        msg = f"permissions must be int or None, got {type(permissions).__name__}"
        raise TypeError(msg)

    if isinstance(target_type, str):
        try:
            target_type = TargetType(target_type.lower())
        except ValueError as e:
            msg = 'If target_type is a string, it must be either "file" or "directory".'
            raise ValueError(msg) from e
    elif isinstance(target_type, TargetType):
        pass
    else:
        msg = (
            "target_type must be a string ('file'|'directory') or a TargetType enum "
            f"(TargetType.FILE|TargetType.DIRECTORY), not a {type(target_type).__name__}: {target_type!r}"
        )
        raise TypeError(msg)

    if target_type == TargetType.DIRECTORY:
        _ensure_directory(path, allow_existing=allow_existing)
    else:
        _ensure_file(path, allow_existing=allow_existing)

    if permissions is not None:
        if platform.system() not in {"Linux", "Darwin"}:
            msg = "Setting permissions is supported only on POSIX platforms."
            raise NotImplementedError(msg)

        _set_posix_permissions(path, permissions)

    return path
