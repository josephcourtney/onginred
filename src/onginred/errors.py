"""Custom exception types for onginred."""

from __future__ import annotations


class OnginredError(Exception):
    """Base class for package-specific exceptions."""


class InvalidTimeRangeError(OnginredError):
    """Raised when a time range specifier is malformed."""


class DescriptorTypeError(OnginredError):
    """Raised when an invalid descriptor type is supplied."""


class InvalidSocketKeyError(OnginredError):
    """Raised when socket definitions contain unsupported keys."""
