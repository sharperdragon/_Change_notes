"""Shared parsing helpers for config values."""

from __future__ import annotations

# --------------------------- USER-TUNABLE CONSTANTS ---------------------------
TRUE_BOOL_STRINGS = {"1", "true", "t", "yes", "y", "on"}
FALSE_BOOL_STRINGS = {"0", "false", "f", "no", "n", "off"}
# -----------------------------------------------------------------------------


def parse_bool(value, default: bool = False) -> bool:
    """Parse bool-like strings/numbers while preserving a fallback default."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in TRUE_BOOL_STRINGS:
            return True
        if lowered in FALSE_BOOL_STRINGS:
            return False
    return default
