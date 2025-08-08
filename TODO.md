* [x] Split `LaunchdService` into smaller single-responsibility-principle-focused components:
  * Delegate `launchctl` invocation to a `LaunchctlClient`.
* [x] Define protocol interfaces:
  * Create `CommandRunner` protocol to formalize runner signature (`__call__` with subprocess args).
* [x] Extract default paths to `config.py` module:
  * `DEFAULT_LOG_LOCATION = Path("/var/log/")`
  * `DEFAULT_INSTALL_LOCATION = Path.home() / "Library" / "LaunchAgents"`
  * `DEFAULT_LAUNCHCTL_PATH = Path("/bin/launchctl")`
* [x] Centralize configuration constants across modules for clarity and reuse.
* [x] Add structured logging across:
  * Path validation and file I/O
  * `launchctl` command execution
  * `.plist` serialization and installation
* [x] Clarify implicit behavior:
  * Make `LaunchdSchedule.to_plist_dict()` behavior more explicit or document interactions between subcomponents more clearly.
* [x] Split large conditionals and logic inside `KeepAliveConfig.as_plist` into smaller helper methods.
* [x] Add docstrings to internal helper classes/functions, especially ones that perform transformation logic.
* [x] Formalize and type-check the `runner` callable using a defined protocol.
* [x] Introduce mocks for `LaunchctlClient` in future test cases after component split.
