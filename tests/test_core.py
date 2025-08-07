import shutil
import subprocess

import onginred


class DummyFile:
    def __truediv__(self, other):
        return self

    def read_text(self, encoding="utf-8"):
        return "<plist/>"


def test_launchctl_install(monkeypatch, tmp_path):
    dummy_plist = tmp_path / "fake.plist"

    monkeypatch.setattr("onginred.core.files", lambda _: DummyFile())
    monkeypatch.setattr("onginred.core.PLIST_PATH", dummy_plist)
    monkeypatch.setattr("pathlib.Path.write_text", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("subprocess.run", lambda *_args, **_kwargs: None)

    onginred.install()


def test_launchctl_uninstall(monkeypatch, tmp_path):
    dummy_plist = tmp_path / "fake.plist"
    dummy_plist.touch()

    monkeypatch.setattr("onginred.core.PLIST_PATH", dummy_plist)
    monkeypatch.setattr("subprocess.run", lambda *_, **__: None)

    onginred.uninstall()
    assert not dummy_plist.exists()


def test_launchctl_install_creates_dir_and_load(monkeypatch, tmp_path):
    # Simulate missing ~/Library/LaunchAgents and record the load call
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    la = home / "Library" / "LaunchAgents"
    if la.exists():
        shutil.rmtree(la)

    # Patch files() to return our dummy, and PLIST_PATH to inside tmp
    monkeypatch.setattr(onginred, "files", lambda _: DummyFile())
    dummy_plist = la / "com.foo.bar.plist"
    monkeypatch.setattr(onginred, "PLIST_PATH", dummy_plist)

    calls = []
    monkeypatch.setattr(subprocess, "run", lambda args, check: calls.append(args))

    onginred.core.install()

    # It should have created the LaunchAgents directory and invoked load
    assert la.exists()
    assert calls
    assert "load" in calls[0]


def test_launchctl_uninstall_removes_and_unloads(monkeypatch, tmp_path):
    # Ensure unload is called and plist file removed
    home = tmp_path / "home2"
    monkeypatch.setenv("HOME", str(home))
    la = home / "Library" / "LaunchAgents"
    la.mkdir(parents=True, exist_ok=True)
    dummy_plist = la / "com.foo.bar.plist"
    dummy_plist.write_text("x")

    monkeypatch.setattr(onginred, "PLIST_PATH", dummy_plist)
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda args, check: calls.append(args))

    # Should not raise
    onginred.uninstall()

    assert not dummy_plist.exists()
    assert calls
    assert "unload" in calls[0]
