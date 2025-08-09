# onginred

**Onginred** is a Python library and CLI tool for defining, configuring, and managing macOS `launchd` services programmatically.

It provides:

- A **Python API** for building, installing, and uninstalling launchd jobs in code.
- A **CLI** for scaffolding, inspecting, installing, and uninstalling jobs without manual `plutil` or `launchctl`.

---

## Meaning

**onginred** /ˈɒn.kɪn.rɛd/  
1. the act of guiding the beginning of a task, journey, or enterprise  
   From Anglish, from Old English *onginrǣd*, a compound of *ongin* ("beginning, undertaking") and *rǣd* ("counsel, advice, plan").

---

## Features

- **Pydantic-based configuration models** — safer, validated `.plist` generation.
- **Composable scheduling** — cron, fixed times, file system triggers, event triggers.
- **Behavior tuning** — keep-alive, throttling, exit handling.
- **Automatic plist installation/uninstallation** — handles `launchctl` internally.
- **Cross-platform safety** — validation works anywhere; install/uninstall is macOS-only.

---

## Installation

```bash
pip install onginred
````

Requires **Python 3.13+**.

---

## Next steps

* [CLI Usage](cli.md) — learn the command-line interface
* [Python API](api.md) — use the library programmatically
* [Scheduling & Triggers](scheduling.md) — available trigger types
* [Development](development.md) — contributing, testing, and linting

