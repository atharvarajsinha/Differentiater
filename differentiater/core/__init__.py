"""Core algorithms: the Myers engine and everything built directly on it."""

from differentiater.core.char_diff import diff_characters
from differentiater.core.line_diff import diff_lines
from differentiater.core.myers import EditLimitExceeded, myers_diff
from differentiater.core.patch import apply_character_operations, apply_operations

__all__ = [
    "EditLimitExceeded",
    "apply_character_operations",
    "apply_operations",
    "diff_characters",
    "diff_lines",
    "myers_diff",
]
