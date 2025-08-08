## [0.1.0] - 2025-08-09

### Added
- add CLI for scaffolding and inspecting plist files
- add asynchronous install/uninstall helpers
- add builder with fluent schedule configuration
- add property-based tests using Hypothesis
- add quick-start usage example and repr helpers

## [0.0.6] - 2025-08-08

### Added
- add alias generator to simplify model field aliases
- add typed dicts for `to_plist_dict` return types
- add atomic plist write helper for safer file writes
- add JSON configuration loader for schedules

### Changed
- replace generic exceptions with descriptive subclasses

## [0.0.5] - 2025-08-08

### Added
- add launchctl client and command runner protocol
- add centralized configuration constants and structured logging

### Changed
- refactor keep-alive helpers and schedule serialization
- delegate launchctl invocation to dedicated client

## [0.0.4] - 2025-08-08

### Added
- extract triggers, sockets, behavior and service modules
- introduce cron helper and injectable subprocess runner
- add keep-alive configuration tests

### Changed
- replace KeepAliveConfig.build with as_plist and update LaunchBehavior
- refine suppression window expansion to return hour/minute pairs

## [0.0.3] - 2025-08-08

### Added
- add regression tests for default model outputs
- add edge-case tests for Program precedence and socket conflicts

### Changed
- remove redundant validation in schedule and socket helpers
- strengthen cron field parsing with explicit range validation
- document pydantic-based configuration

## [0.0.2] - 2025-03-07

### Added
- add pydantic-based models replacing dataclasses for launchd configuration
- add explicit test coverage for Program field precedence and socket validation

### Changed
- refactor core builders into declarative models
- enhance file permission checks for existing files

