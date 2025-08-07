# AGENTS.md

## Purpose

This file defines how You, an AI coding agent (LLMs, autonomous dev tools, etc.), must operate when contributing to this project.

## Project Context

You are contributing to `brocli`.

## Role


Your responsibilities include:

* Editing Python source files under `src/brocli/`
* Creating or editing test files under `tests/`
* Preserving output determinism, testability, and extensibility
* Respecting existing CLI conventions and internal architecture

## Directory Constraints

* Source code: `src/brocli/`
* Tests: `tests/`
* Do not write, or create files outside these directories unless explicitly instructed.

## Tooling Requirements

Before proposing code, validate all changes using the tools below.

If any command fails due to missing executables or environment configuration, emit a diagnostic message and request clarification from the user.

### Package Management

* Command: `uv`
* Rules: use `uv` for all package management including adding and removing dependencies

### Linting

* Command: `.venv/bin/ruff check src/ tests/`
* Rules: Defined in `pyproject.toml` and any referenced config files

### Formatting

* Command: `.venv/bin/ruff format src/ tests/`

### Static Typing

* Command: `.venv/bin/ty check src/ tests/`
* Syntax: Use Python 3.13–compatible type annotations
* Constraints: Must follow `pyproject.toml` settings

> If `ty` is not available in `.venv/bin/`, log a failure notice, emit proposed code as a Markdown patch, and halt execution.

### Testing

* Command: `.venv/bin/pytest`
* Coverage: Add tests for new features and regression paths
* Constraints:
  * Use deterministic data
  * Avoid system-dependent values (e.g., timestamps, user paths)
  * Use `.venv/bin/pytest` to generate coverage

> If coverage decreases from the baseline in `coverage.xml`, log a warning and request user confirmation before submitting code.

## Behavior Constraints

* Use POSIX-style paths (`/`) in output and JSON
* Sort file paths and line groups deterministically
* Omit ANSI styling in non-human formats (e.g., JSON)
* No I/O outside `src/`, `tests/`, or `TODO.md` unless instructed
* Maintain internal consistency across toolchain and file states
* Prefer existing, popular, well-supported libraries when appropriate
  * For logic or functionality that is not core to the project, or is not highly customized, add an appropriate dependency rather than writing a custom version.

## Logging and Progress Tracking

### To-Do List Maintenance

* As you complete items from `TODO.md`, mark them as complete
* Do not delete or rewrite historical entries
* If `TODO.md` is missing, create a new file and notify the user

### Changelog Maintenance


Follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format:

* Example heading: `## [1.2.3] - 2025-08-02`
* Allowed sections: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`
* Each bullet must:

  * Begin with a lowercase imperative verb (e.g., “add”, “fix”)
  * Follow Markdown syntax

Ensure:

* Changelog matches the actual code changes
* Version in `pyproject.toml` is updated
* Historical entries are never modified
* If `CHANGELOG.md` is missing, create a stub file and note this

Example:

```markdown
## [1.4.0] - 2025-08-02

### Added
- add `--format json` CLI option for machine-readable output

### Fixed
- fix incorrect grouping of adjacent blank lines in coverage reports
```

## Commit Standards

Each commit must pass:

* `.venv/bin/ruff check && .venv/bin/ruff format`
* `.venv/bin/ty check`
* `.venv/bin/pytest`

Use conventional commit messages:

* `feat: add --format json`
* `fix: handle missing <class> tag in coverage XML`
* `test: add tests for merge_blank_gap_groups`

Before submitting a pull request:

* Bump the version in `pyproject.toml` if relevant
* Update `CHANGELOG.md` accordingly

## Prohibited Behavior

* Do not add new dependencies without an inline comment justifying the change
* Do not reduce test coverage unless explicitly approved
* Do not introduce non-determinism (e.g., random output, time-dependent data)
* Do not write outside `src/`, `tests/`, `CHANGELOG.md`, or `TODO.md` unless instructed

## Assumptions and Capabilities

You must assume:

* Each task starts with only the current file state
* You must re-read `TODO.md`, and `CHANGELOG.md` before taking action on historical items

If lacking access to shell or file I/O:

* Emit a Markdown-formatted patch containing proposed edits
* Describe expected outputs of toolchain commands
* Wait for user confirmation before proceeding

## Compliance

All actions must follow this protocol unless:

* Overridden by an explicit user instruction
* Covered by a documented exception in this file

```
```

