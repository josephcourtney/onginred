# Additional Tests
| Area                   | Action                                                                         |
| ---------------------- | ------------------------------------------------------------------------------ |
| `Program` field        | Add explicit test for its precedence over `ProgramArguments`.                  |
| Socket validation      | Add tests for string vs enum errors; test conflicting field combinations.      |
| Empty/invalid job spec | Test what happens when no schedule/event/behavior is set.                      |
| Edge validation        | Add direct unit tests for `validate_range` and `_parse_cron_field`.            |
| Model consistency      | Add regression tests for `.to_plist_dict()` output under default construction. |

# Refactoring Plan: Reduce Boilerplate in `onginred`

## Objective
Replace manual builders and dataclasses with declarative, schema‑based models using `pydantic` (or similar) to eliminate repetitive validation and serialization code.

## Assumptions
- All current `to_plist_dict` logic should be preserved in behavior.
- Existing tests in `tests/` adequately cover functionality.
- Full access to install and depend on `pydantic` is available.

## Steps

### 1. Establish Baseline
- Measure code complexity (e.g. maintainability index via `radon`) to quantify improvements :contentReference[oaicite:1]{index=1}.
- Run full test suite to confirm current behavior.

### 2. Introduce Pydantic Data Models
- Identify sections with repetitive validation (e.g. `TimeTriggers`, `LaunchBehavior`, `SocketConfigBuilder`).
- Create `pydantic.BaseModel` classes for each section, using field types, constraints, and default values (e.g. `conint`, `validator`) :contentReference[oaicite:2]{index=2}.
- Map Pythonic field names to plist key names using `alias`.

### 3. Implement Conversion Logic
- Use `.dict(by_alias=True, exclude_none=True)` to produce serialized output matching plist schema.
- Replace manual `to_plist_dict()` implementations with calls to the `pydantic` model’s serialization.

### 4. Refactor Builders to Use Models
- For code that currently builds dicts with conditional inclusion:
  - Replace with instantiating the pydantic model and serialization.
  - Remove manual validation, relying on model logic.

### 5. Replace Manual Dataclasses Where Appropriate
- Optionally convert lightweight plain dataclasses (without validation) to `@dataclass` or fallback to `pydantic` for consistency.
- Confirm that default and repr functionality is preserved.

### 6. Update Tests
- Incrementally update tests to instantiate new models (or wrappers) instead of older builders.
- Validate that rendered plist dicts remain identical before and after refactor.

### 7. Incremental Migration
- Refactor one component at a time (e.g. time triggers → filesystem triggers → behavior).
- After each component, run tests to ensure no regression :contentReference[oaicite:3]{index=3}.

### 8. Clean Up
- Remove obsolete builder classes (`KeepAliveBuilder`, `SocketConfigBuilder`) after validation passes.
- Remove redundant validation logic.
- Update documentation (`README.md`, `man_launchd_plist.md`) to reflect new usage patterns.

### 9. Final Verification & Measure
- Rerun maintainability metrics to demonstrate reduction in boilerplate and improved code health.
- Confirm all tests still pass.

## Summary of Benefits
- **Less boilerplate**: validation and serialization consolidated in one place via `pydantic` :contentReference[oaicite:4]{index=4}.
- **Improved readability**: clear field definitions and alias mapping replace manual dict assembly.
- **Test safety**: incremental replacement backed by existing test suite ensures stability :contentReference[oaicite:5]{index=5}.
