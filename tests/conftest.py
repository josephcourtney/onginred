import pytest

MAX_OUTPUT_LINES = 32


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Limit captured output per failing test."""
    if report.when == "call" and report.failed:
        new_sections: list[tuple[str, str]] = []
        for title, content in report.sections:
            if title.startswith(("Captured stdout", "Captured stderr")):
                lines = content.splitlines()
                if len(lines) > MAX_OUTPUT_LINES:
                    truncated = "\n".join([*lines[:MAX_OUTPUT_LINES], "... [output truncated]"])
                    new_sections.append((title, truncated))
                else:
                    new_sections.append((title, content))
            else:
                new_sections.append((title, content))
        report.sections = new_sections
