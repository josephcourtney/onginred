# onginred

**Onginred** is a Python project that programmatically defines, configures, and manages macOS `launchd` services. Its core purpose is to provide a structured, Pythonic interface for building and installing `launchd` property lists (`.plist` files), which are used by macOS to manage background agents and daemons.

## Meaning 
  **onginred** /ˈɒn.kɪn.rɛd/
  1. the act of guiding the beginning of a task, journey, or enterprise
  From Anglish, from Old English *onginrǣd*, a compound of *ongin* ("beginning, undertaking") and *rǣd* ("counsel, advice, plan").

## Core capabilities:

* **Define launch configurations** using Python data structures instead of writing raw XML property lists.
* **Support for time-based scheduling**, file system triggers, sockets, Mach services, and more via composable classes:

  * `TimeTriggers`, `FilesystemTriggers`, `EventTriggers`, and `LaunchBehavior`.
* **Export to valid `launchd.plist` format** using `plistlib`.
* **Installation and removal** of launch agents using `launchctl`.
* **Support for advanced features** like suppression windows, cron expressions, socket configurations, and restart conditions.
