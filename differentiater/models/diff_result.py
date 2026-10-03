"""Structured, renderer-independent representation of a diff."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Sequence


class OperationType(str, Enum):
    """Kinds of operations a diff can contain.

    The enum subclasses ``str`` so members compare equal to the plain
    strings produced by the Myers engine (``"equal"``, ``"insert"``, ...).
    """

    EQUAL = "equal"
    INSERT = "insert"
    DELETE = "delete"
    MODIFY = "modify"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CharacterOperation:
    """A run of characters inside a modified line."""

    operation: OperationType
    text: str


@dataclass
class DiffOperation:
    """One line-level operation.

    Line numbers are 1-based and refer to the original files (or to the
    logical view, for notebooks).  ``None`` means "not present on that side".
    """

    operation: OperationType
    old_line_number: Optional[int]
    new_line_number: Optional[int]
    old_text: Optional[str]
    new_text: Optional[str]
    char_operations: Optional[List[CharacterOperation]] = None

    @property
    def is_change(self) -> bool:
        return self.operation != OperationType.EQUAL


@dataclass(frozen=True)
class FileInfo:
    """Metadata about one compared input."""

    path: str
    line_count: int
    encoding: str = "utf-8"
    line_ending: str = "LF"
    has_final_newline: bool = True
    kind: str = "text"


@dataclass(frozen=True)
class DiffSummary:
    """Counts derived from the actual diff operations, never from line counts."""

    old_lines: int
    new_lines: int
    inserted: int
    deleted: int
    modified: int
    unchanged: int
    chars_inserted: int = 0
    chars_deleted: int = 0

    @property
    def line_delta(self) -> int:
        return self.new_lines - self.old_lines

    @property
    def total_changes(self) -> int:
        return self.inserted + self.deleted + self.modified

    @property
    def is_identical(self) -> bool:
        return self.total_changes == 0

    @classmethod
    def from_operations(
        cls,
        operations: Sequence[DiffOperation],
        old_lines: int,
        new_lines: int,
    ) -> "DiffSummary":
        counts = {kind: 0 for kind in OperationType}
        chars_inserted = chars_deleted = 0
        for op in operations:
            counts[op.operation] += 1
            for char_op in op.char_operations or ():
                if char_op.operation == OperationType.INSERT:
                    chars_inserted += len(char_op.text)
                elif char_op.operation == OperationType.DELETE:
                    chars_deleted += len(char_op.text)
        return cls(
            old_lines=old_lines,
            new_lines=new_lines,
            inserted=counts[OperationType.INSERT],
            deleted=counts[OperationType.DELETE],
            modified=counts[OperationType.MODIFY],
            unchanged=counts[OperationType.EQUAL],
            chars_inserted=chars_inserted,
            chars_deleted=chars_deleted,
        )


@dataclass
class DiffResult:
    """The complete outcome of comparing file A with file B."""

    old: FileInfo
    new: FileInfo
    operations: List[DiffOperation]
    summary: DiffSummary
    ignore_space: bool = False
    ignore_blank_lines: bool = False
    notes: List[str] = field(default_factory=list)

    @property
    def has_differences(self) -> bool:
        return not self.summary.is_identical

    @property
    def changes(self) -> List[DiffOperation]:
        return [op for op in self.operations if op.is_change]
