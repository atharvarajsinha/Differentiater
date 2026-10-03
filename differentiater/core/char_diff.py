"""Character-level diff built on the same Myers engine as the line diff."""

from __future__ import annotations

from typing import List, Optional, Sequence

from differentiater.core.myers import EditLimitExceeded, EditOperation, myers_diff
from differentiater.models.diff_result import CharacterOperation, OperationType

#: Safety bound for character diffs of very long, very different lines.
DEFAULT_MAX_CHAR_EDITS = 2000


def diff_characters(
    old: str, new: str, *, max_edits: Optional[int] = None
) -> List[CharacterOperation]:
    """Diff two strings character by character using Myers' algorithm.

    Consecutive characters with the same operation are merged into runs, so
    ``"return a + b"`` -> ``"return a + b + c"`` yields
    ``[equal "return a + b", insert " + c"]``.

    Raises:
        EditLimitExceeded: if ``max_edits`` is given and exceeded.
    """
    script = myers_diff(list(old), list(new), max_edits=max_edits)
    return merge_runs(script)


def diff_characters_bounded(
    old: str, new: str, *, max_edits: int = DEFAULT_MAX_CHAR_EDITS
) -> List[CharacterOperation]:
    """Like :func:`diff_characters` but never explodes on pathological input.

    If the exact diff needs more than ``max_edits`` edits the whole line is
    reported as replaced (one delete run plus one insert run).
    """
    try:
        return diff_characters(old, new, max_edits=max_edits)
    except EditLimitExceeded:
        return whole_line_replacement(old, new)


def whole_line_replacement(old: str, new: str) -> List[CharacterOperation]:
    """Character operations describing ``old`` fully replaced by ``new``."""
    runs = []
    if old:
        runs.append(CharacterOperation(OperationType.DELETE, old))
    if new:
        runs.append(CharacterOperation(OperationType.INSERT, new))
    return runs


def merge_runs(script: Sequence[EditOperation]) -> List[CharacterOperation]:
    """Collapse a per-character edit script into runs of equal operation."""
    runs: List[CharacterOperation] = []
    current_op: Optional[str] = None
    buffer: List[str] = []
    for operation, char in script:
        if operation != current_op and buffer:
            runs.append(CharacterOperation(OperationType(current_op), "".join(buffer)))
            buffer = []
        current_op = operation
        buffer.append(char)
    if buffer:
        runs.append(CharacterOperation(OperationType(current_op), "".join(buffer)))
    return runs


def old_side(operations: Sequence[CharacterOperation]) -> str:
    """Reconstruct the old string from character operations."""
    return "".join(
        op.text for op in operations if op.operation != OperationType.INSERT
    )


def new_side(operations: Sequence[CharacterOperation]) -> str:
    """Reconstruct the new string from character operations."""
    return "".join(
        op.text for op in operations if op.operation != OperationType.DELETE
    )


def similarity_ratio(operations: Sequence[CharacterOperation]) -> float:
    """``2 * matched / (len(old) + len(new))``; 1.0 for two empty strings."""
    matched = sum(
        len(op.text) for op in operations if op.operation == OperationType.EQUAL
    )
    total = len(old_side(operations)) + len(new_side(operations))
    return 1.0 if total == 0 else 2.0 * matched / total
