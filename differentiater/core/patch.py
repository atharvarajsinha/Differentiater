"""Apply diff operations back to the original -- the reconstruction check.

``apply_operations(a, diff(a, b)) == b`` must hold for every diff the project
produces.  The functions here validate every step against the original, so a
wrong edit script fails loudly instead of silently producing ``b``.
"""

from __future__ import annotations

from typing import Any, List, Sequence, Union

from differentiater.models.diff_result import (
    CharacterOperation,
    DiffOperation,
    OperationType,
)

Operation = Union[DiffOperation, "tuple[str, Any]"]


def apply_operations(original: Sequence[Any], operations: Sequence[Operation]) -> List[Any]:
    """Rebuild the target sequence from ``original`` and ``operations``.

    Accepts either raw Myers edit scripts (``("equal", item)`` tuples) or
    :class:`DiffOperation` objects from the line diff.

    Raises:
        ValueError: if an operation does not match the original sequence.
    """
    result: List[Any] = []
    position = 0
    for op in operations:
        kind, old_item, new_item = _unpack(op)
        if kind == OperationType.INSERT:
            result.append(new_item)
            continue
        if position >= len(original) or original[position] != old_item:
            raise ValueError(
                f"operation {kind} at position {position} does not match the original"
            )
        position += 1
        if kind != OperationType.DELETE:  # equal or modify keep a line
            result.append(new_item)
    if position != len(original):
        raise ValueError(f"operations consumed {position} of {len(original)} items")
    return result


def apply_character_operations(original: str, operations: Sequence[CharacterOperation]) -> str:
    """Rebuild the new string of a modified line from its character diff."""
    pieces: List[str] = []
    position = 0
    for op in operations:
        if op.operation == OperationType.INSERT:
            pieces.append(op.text)
            continue
        end = position + len(op.text)
        if original[position:end] != op.text:
            raise ValueError(f"character run {op.text!r} does not match at {position}")
        position = end
        if op.operation == OperationType.EQUAL:
            pieces.append(op.text)
    if position != len(original):
        raise ValueError(f"operations consumed {position} of {len(original)} characters")
    return "".join(pieces)


def _unpack(op: Operation) -> "tuple[str, Any, Any]":
    if isinstance(op, DiffOperation):
        return op.operation, op.old_text, op.new_text
    kind, item = op
    return kind, item, item
