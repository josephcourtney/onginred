# Scheduling & Triggers

Onginred supports multiple trigger types, all combinable in one job.

---

## Time triggers

- `add_cron(expr)` — cron-style scheduling (`"0 6 * * *"`)
- `add_fixed_time(hour, minute)` — run at fixed time
- `set_start_interval(seconds)` — run every N seconds
- `add_suppression_window("HH:MM-HH:MM")` — define off-periods

---

## Filesystem triggers

- `add_watch_path(path)` — trigger when files change
- `add_queue_directory(path)` — trigger when files added, processed serially
- `enable_start_on_mount()` — trigger when a filesystem mounts

---

## Event triggers

- `add_launch_event(subsystem, name, descriptor_dict)`
- `add_socket(name, **socket_opts)`
- `add_mach_service(name, reset_at_close=True)`

---

## Behavior tuning

Use `LaunchBehavior` to configure run conditions:

```python
from onginred.behavior import LaunchBehavior

behavior = LaunchBehavior(
    run_at_load=True,
    keep_alive=True,
    throttle_interval=60,
)
````

