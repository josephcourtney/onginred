# onginred

**onginred** is a Python library and CLI tool for defining, configuring, and managing macOS `launchd` services programmatically.

It lets you:

- Build `.plist` files with validated, composable schedules.
- Install/uninstall launchd jobs directly — no manual `plutil` or `launchctl` needed.
- Trigger jobs by time, file changes, events, or combinations thereof.
- Use either a **Python API** or a **CLI** workflow.

---

## Meaning

**onginred** /ˈɒn.kɪn.rɛd/  
> the act of guiding the beginning of a task, journey, or enterprise  
> From Anglish, from Old English *onginrǣd*, a compound of *ongin* ("beginning, undertaking") and *rǣd* ("counsel, advice, plan").

---

## Installation

```bash
pip install onginred
````

Requires **Python 3.13+**. Install on macOS for full functionality (validation runs cross-platform).

---

## Quick examples

**CLI — timed job**

```bash
onginred install com.example.hello \
  --run-at-load \
  --start-interval 300 \
  --log-dir "$HOME/Library/Logs" \
  --create-log-files \
  -- "$HOME/bin/hello.sh"
```

**Python API — file watcher**

```python
from pathlib import Path
from onginred.schedule import LaunchdSchedule
from onginred.service import LaunchdService

sched = LaunchdSchedule()
sched.behavior.run_at_load = True
sched.fs.add_watch_path("/path/to/watch")

svc = LaunchdService(
    bundle_identifier="com.example.onchange",
    command=["/path/to/onchange.sh"],
    schedule=sched,
    log_dir=Path.home() / "Library" / "Logs",
    create_dir=True,
)
svc.install()
```

---

## Documentation

Full docs (CLI flags, API reference, scheduling) are in:

* 📖 **Website:** [https://josephcourtney.github.io/onginred/](https://josephcourtney.github.io/onginred/) (enable via GitHub Pages)
* 📚 **Markdown:** [docs/index.md](docs/index.md)

Start with:

* [CLI Usage](docs/cli.md)
* [Python API](docs/api.md)
* [Scheduling & Triggers](docs/scheduling.md)

---

## Development

```bash
git clone https://github.com/josephcourtney/onginred.git
cd onginred
python -m venv venv
source venv/bin/activate
pip install -e .[dev]
```

* Linting: `ruff check`
* Formatting: `ruff format`
* Testing: `pytest`
* Type checking: `ty check`

---

## License

GPL-3.0-only

