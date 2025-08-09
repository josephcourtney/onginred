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

Requires **Python 3.13+**.
Install on macOS for full functionality. Validation runs cross-platform.

---

## Quick examples
Here’s a **short, polished `README.md`** designed for GitHub — concise enough for a landing page, but still informative and pointing people toward the full docs you now have in `docs/`.

---

````markdown

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

Full documentation, including all CLI flags, Python API reference, and advanced scheduling features, is available at: 
https://josephcourtney.github.io/onginred/ (coming soon...)

📖 **[Docs](docs/index.md)** — start with:

* [CLI Usage](docs/cli.md)
* [Python API](docs/api.md)
* [Scheduling & Triggers](docs/scheduling.md)

---

## Development

```bash
git clone https://github.com/yourname/onginred.git
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

