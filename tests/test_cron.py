import pytest

from onginred.cron import expand, validate_range


def test_validate_range_boundaries():
    validate_range("Minute", 0, 0, 59)
    validate_range("Minute", 59, 0, 59)


@pytest.mark.parametrize(
    ("expr", "first"),
    [
        ("1-3 0 * * *", [{"Minute": 1, "Hour": 0}, {"Minute": 2, "Hour": 0}, {"Minute": 3, "Hour": 0}]),
        ("*/30 1 * * *", [{"Minute": 0, "Hour": 1}, {"Minute": 30, "Hour": 1}]),
    ],
)
def test_cron_expand(expr, first):
    entries = expand(expr)
    assert entries[: len(first)] == first


@pytest.mark.parametrize("expr", ["0-100 0 * * *", "*/0 0 * * *"])
def test_cron_expand_invalid(expr):
    with pytest.raises(ValueError, match=r"."):
        expand(expr)


def test_validate_range_error():
    with pytest.raises(ValueError, match=r"."):
        validate_range("Minute", 60, 0, 59)
