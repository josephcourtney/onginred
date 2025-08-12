import re
import shutil
import subprocess
from pathlib import Path

import pytest
import requests

from onginred import cli

DOCS_DIRS = ["docs", "."]  # check docs/ and root README.md

# Match [text](url) but skip images ![alt](...)
LINK_RE = re.compile(r"(?<!!)\[.*?\]\((.*?)\)")

# Schemes to skip entirely
SKIP_SCHEMES = ("mailto:", "tel:")

# Domains or patterns to skip (e.g., localhost)
SKIP_PATTERNS = ("127.0.0.1", "localhost")


def _iter_links():
    for docs_dir in DOCS_DIRS:
        for path in Path(docs_dir).rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for match in LINK_RE.findall(text):
                if match.startswith(SKIP_SCHEMES) or any(p in match for p in SKIP_PATTERNS):
                    continue
                yield path, match


@pytest.mark.skipif(shutil.which("mkdocs") is None, reason="mkdocs not installed")
def test_mkdocs_build_strict(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]

    site_dir = tmp_path / "site"
    cmd = ["mkdocs", "build", "--strict", "--site-dir", str(site_dir)]
    proc = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        pytest.fail(f"mkdocs build failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    assert site_dir.exists()


def _get_help_text(argv):
    with pytest.raises(SystemExit):
        cli.main([*argv, "--help"])
    # argparse prints help to stdout when raising SystemExit
    # so we re-run capturing stdout via pytest capsys in the test.
    # We'll wrap each call in its own test to use capsys.


def test_root_help_lists_commands(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    out = capsys.readouterr().out
    for cmd in ["scaffold", "inspect", "install", "uninstall"]:
        assert cmd in out


def test_install_help_has_key_flags(capsys):
    with pytest.raises(SystemExit):
        cli.main(["install", "--help"])
    out = capsys.readouterr().out
    for flag in [
        "--run-at-load",
        "--keep-alive",
        "--start-interval",
        "--cron",
        "--at",
        "--suppress",
        "--watch",
        "--queue",
        "--start-on-mount",
        "--exit-timeout",
        "--throttle-interval",
        "--log-dir",
        "--log-name",
        "--stdout-log",
        "--stderr-log",
        "--create-log-files",
    ]:
        assert flag in out


@pytest.mark.parametrize(("path", "url"), list(_iter_links()))
def test_links_ok(path, url):
    """Check that all Markdown links are reachable."""
    if url.startswith("#") or (not url.startswith("http") and not url.startswith("/")):
        pytest.skip(f"Local anchor or relative link: {url}")

    try:
        resp = requests.head(url, allow_redirects=True, timeout=10)
        if resp.status_code >= 400:
            # Some servers don't respond well to HEAD, try GET
            resp = requests.get(url, allow_redirects=True, timeout=10)
        assert resp.status_code < 400, f"{url} -> {resp.status_code}"
    except requests.RequestException as e:
        pytest.fail(f"Request to {url} failed: {e}")
