import os
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest

from onginred import file_io
from onginred.file_io import TargetType, _set_posix_permissions, ensure_path


def test_create_new_file_in_default_directory(fs):
    # Simulate default directory and no existing target
    default_dir = Path("/default")
    result = ensure_path("foo.txt", default_directory=default_dir, target_type="file")
    assert isinstance(result, Path)
    assert result.exists()
    assert result.is_file()
    assert result.parent == default_dir


def test_existing_file_not_allowed(fs):
    fs.create_file("/test.txt")
    with pytest.raises(FileExistsError):
        ensure_path("/test.txt", allow_existing=False, target_type=TargetType.FILE)


def test_existing_file_allowed_but_unwritable(fs):
    file_path = Path("/file.txt")
    fs.create_file(str(file_path), contents="hi")
    # Make unwritable
    file_path.chmod(0o444)
    with pytest.raises(OSError, match="not writable"):
        ensure_path(str(file_path), allow_existing=True, target_type="file")


def test_existing_file_allowed_and_writable(fs):
    file_path = Path("/good.txt")
    fs.create_file(str(file_path), contents="hi")
    file_path.chmod(0o666)
    result = ensure_path(str(file_path), allow_existing=True, target_type="file")
    assert result == file_path


def test_directory_creation(fs):
    default = Path("/mydir")
    result = ensure_path("subdir", default_directory=default, target_type="directory")
    assert result == Path("/mydir/subdir")
    assert result.is_dir()


def test_existing_directory_not_allowed(fs):
    fs.create_dir("/existing_dir")
    with pytest.raises(FileExistsError):
        ensure_path("/existing_dir", allow_existing=False, target_type="directory")


def test_existing_directory_allowed(fs):
    fs.create_dir("/allowed_dir")
    result = ensure_path("/allowed_dir", allow_existing=True, target_type="directory")
    assert result == Path("/allowed_dir")


def test_invalid_target_type(fs):
    with pytest.raises(ValueError, match='must be either "file" or "directory"'):
        ensure_path("/a", target_type="invalid")


def test_permissions_applied_on_create(fs):
    path = ensure_path("/perm.txt", permissions=0o640, target_type="file")
    assert path.exists()
    if os.name != "posix":
        with pytest.raises(NotImplementedError):
            ensure_path("/perm2.txt", permissions=0o600, target_type="file")
    else:
        mode = path.stat().st_mode & 0o777
        assert mode == 0o640


def test_non_string_target_type_accepts_enum(fs):
    result = ensure_path("/enum.txt", target_type=TargetType.FILE)
    assert result.exists()


def test_symlink_resolution_behavior(fs):
    # create dir and symlink
    fs.create_dir("/real")
    fs.create_symlink("/link", "/real")
    real_file = "/real/file.txt"
    fs.create_file(real_file)
    # Without resolving: path stays as link
    out = ensure_path("/link/file.txt", resolve_symlinks=False, allow_existing=True)
    assert "link" in str(out)
    # With resolving: should point to /real/file.txt
    out2 = ensure_path("/link/file.txt", resolve_symlinks=True, allow_existing=True)
    assert "real" in str(out2)


def test_relative_path_no_default_directory(fs):
    with pytest.raises(ValueError, match="Relative path provided but no default_directory specified"):
        ensure_path("rel.txt", default_directory=None)


def test_invalid_permission_type(fs):
    with pytest.raises(TypeError):
        ensure_path("/a.txt", permissions=cast("Any", "644"))


def test_invalid_target_type_type(fs):
    with pytest.raises(TypeError):
        ensure_path("/a", target_type=cast("Any", 123))


def test_set_posix_permissions_chmod_fails(monkeypatch):
    if os.name != "posix":
        pytest.skip("POSIX-only test")

    def raise_oserror(self, mode):
        msg = "chmod failed"
        raise OSError(msg)

    monkeypatch.setattr(Path, "chmod", raise_oserror)
    with pytest.raises(OSError, match="Failed to set permissions"):
        _set_posix_permissions(Path("/some/path"), 0o600)


def test_invalid_target_type_type_object(tmp_path):
    with pytest.raises(TypeError, match="Invalid target type"):
        ensure_path(cast("Any", 12345), default_directory=tmp_path, target_type="file")


def test_invalid_default_directory_type():
    with pytest.raises(TypeError, match="default_directory must be a Path object"):
        ensure_path("file.txt", default_directory=cast("Any", 123), target_type="file")


def test_file_exists_where_directory_expected_disallow(fs):
    fs.create_file("/not_a_dir")
    with pytest.raises(FileExistsError, match="Directory exists at"):
        ensure_path("/not_a_dir", target_type="directory", allow_existing=False)


def test_directory_creation_oserror(monkeypatch):
    def raise_oserror(*args, **kwargs):
        msg = "mkdir failed"
        raise OSError(msg)

    monkeypatch.setattr(Path, "mkdir", raise_oserror)
    with pytest.raises(OSError, match="Cannot create directory"):
        ensure_path("/some/newdir", target_type="directory")


def test_file_creation_parent_mkdir_fails(monkeypatch):
    def raise_oserror(*args, **kwargs):
        msg = "mkdir failed"
        raise OSError(msg)

    monkeypatch.setattr(Path, "mkdir", raise_oserror)
    with pytest.raises(OSError, match="Failed to create parent directory"):
        ensure_path("/path/to/file.txt", target_type="file")


def test_file_expected_but_directory_found(fs):
    fs.create_dir("/some_dir")
    with pytest.raises(IsADirectoryError):
        ensure_path("/some_dir", target_type="file", allow_existing=True)


def test_file_touch_raises_oserror(monkeypatch, tmp_path):
    target = tmp_path / "badfile.txt"

    def touch_side_effect(*args, **kwargs):
        msg = "touch failed"
        raise OSError(msg)

    monkeypatch.setattr(Path, "touch", touch_side_effect)

    with pytest.raises(OSError, match="Cannot create file"):
        ensure_path(target, allow_existing=False, target_type="file")


def test_permissions_on_non_posix(monkeypatch, fs):
    monkeypatch.setattr("platform.system", lambda: "Windows")
    with pytest.raises(NotImplementedError):
        ensure_path("/some/file.txt", permissions=0o644, target_type="file")


def test_string_target_type_file(fs):
    result = ensure_path("/testfile", target_type="file")
    assert result.exists()


def test_string_target_type_directory(fs):
    result = ensure_path("/testdir", target_type="directory")
    assert result.is_dir()


def test_file_created_during_check(tmp_path):
    target = tmp_path / "race.txt"

    def touch_side_effect(*args, **kwargs):
        msg = "Created during race"
        raise FileExistsError(msg)

    with (
        patch.object(Path, "exists", return_value=False),
        patch.object(Path, "touch", side_effect=touch_side_effect),
        pytest.raises(FileExistsError, match="was created during check"),
    ):
        ensure_path(target, allow_existing=False, target_type="file")


def test_set_posix_permissions_unsupported(monkeypatch):
    monkeypatch.setattr(file_io, "_is_posix", lambda: False)
    with pytest.raises(NotImplementedError):
        file_io._set_posix_permissions(Path("/fake.txt"), 0o644)
