"""Line-level diff: Myers over lines, then classification."""

from __future__ import annotations

from typing import Dict, Hashable, List, Optional, Sequence

from differentiater.core.classifier import classify
from differentiater.core.myers import DELETE, EQUAL, INSERT, myers_diff
from differentiater.core.normalizer import PreparedLines, prepare_lines
from differentiater.models.diff_result import DiffOperation, OperationType
from differentiater.models.document import CompareOptions


def diff_lines(
    old_lines: Sequence[str],
    new_lines: Sequence[str],
    *,
    options: Optional[CompareOptions] = None,
    old_has_final_newline: bool = True,
    new_has_final_newline: bool = True,
) -> List[DiffOperation]:
    """Diff two lists of lines and classify the result.

    Returns EQUAL / INSERT / DELETE / MODIFY operations with old and new line
    numbers.  MODIFY operations carry their character-level diff.
    """
    old = prepare_lines(old_lines, has_final_newline=old_has_final_newline, options=options)
    new = prepare_lines(new_lines, has_final_newline=new_has_final_newline, options=options)
    return diff_prepared(old, new)


def diff_prepared(old: PreparedLines, new: PreparedLines) -> List[DiffOperation]:
    """Diff already-normalised lines and classify the result."""
    return classify(compute_raw_operations(old, new))


def compute_raw_operations(old: PreparedLines, new: PreparedLines) -> List[DiffOperation]:
    """Run Myers on the comparison keys and attach line numbers and text.

    The result only contains EQUAL, INSERT and DELETE operations, exactly as
    Myers produced them.
    """
    old_ids, new_ids = _intern_keys(old.keys, new.keys)
    script = myers_diff(old_ids, new_ids)

    operations: List[DiffOperation] = []
    i = j = 0  # positions in old / new
    for kind, _ in script:
        if kind == EQUAL:
            operations.append(DiffOperation(
                OperationType.EQUAL, old.numbers[i], new.numbers[j],
                old.texts[i], new.texts[j],
            ))
            i += 1
            j += 1
        elif kind == DELETE:
            operations.append(DiffOperation(
                OperationType.DELETE, old.numbers[i], None, old.texts[i], None,
            ))
            i += 1
        elif kind == INSERT:
            operations.append(DiffOperation(
                OperationType.INSERT, None, new.numbers[j], None, new.texts[j],
            ))
            j += 1
    return operations


def _intern_keys(
    old_keys: Sequence[Hashable], new_keys: Sequence[Hashable]
) -> "tuple[List[int], List[int]]":
    """Map each distinct key to a small integer.

    Comparing integers is much cheaper than comparing long strings inside the
    Myers inner loop; equality is preserved exactly.
    """
    table: Dict[Hashable, int] = {}
    old_ids = [table.setdefault(key, len(table)) for key in old_keys]
    new_ids = [table.setdefault(key, len(table)) for key in new_keys]
    return old_ids, new_ids
