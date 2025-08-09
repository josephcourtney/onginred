# Python API

The Python API gives you full control over schedules, triggers, logging, and behavior — and can install/uninstall jobs without touching `launchctl` manually.

---

## Quick start

```python
from pathlib import Path
from onginred.schedule import LaunchdSchedule
from onginred.service import LaunchdService

logs_dir = Path.home() / "Library" / "Logs"
logs_dir.mkdir(parents=True, exist_ok=True)

sched = LaunchdSchedule()
sched.behavior.run_at_load = True
sched.time.set_start_interval(300)  # every 5 minutes

svc = LaunchdService(
    bundle_identifier="com.example.hello",
    command=[str(Path.home() / "bin" / "hello.sh")],
    schedule=sched,
    log_dir=logs_dir,
    log_name="com.example.hello",
    create_dir=True,
)

svc.install()   # writes plist & calls launchctl bootstrap
# svc.uninstall()  # when done
````

---

## File-watching job

```python
sched = LaunchdSchedule()
sched.behavior.run_at_load = True
sched.fs.add_watch_path("/path/to/watch")
sched.fs.add_queue_directory("/path/to/queue")

svc = LaunchdService(
    bundle_identifier="com.example.onchange",
    command=["/path/to/onchange.sh"],
    schedule=sched,
    log_dir=Path.home() / "Library" / "Logs",
    log_name="com.example.onchange",
    create_dir=True,
)
svc.install()
```

