"""Utility helpers for onginred."""

from __future__ import annotations


def to_camel(s: str) -> str:
    """Convert ``snake_case`` strings to ``CamelCase``.

    Used as a Pydantic ``alias_generator`` to reduce repetitive ``alias``
    declarations across models.
    """
    return "".join(part.capitalize() or "_" for part in s.split("_"))
