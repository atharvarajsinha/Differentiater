"""Data models shared by the core, parsers and renderers."""

from differentiater.models.diff_result import (
    CharacterOperation,
    DiffOperation,
    DiffResult,
    DiffSummary,
    FileInfo,
    OperationType,
)
from differentiater.models.document import (
    CompareOptions,
    LoadedDocument,
    ParseOptions,
)

__all__ = [
    "CharacterOperation",
    "CompareOptions",
    "DiffOperation",
    "DiffResult",
    "DiffSummary",
    "FileInfo",
    "LoadedDocument",
    "OperationType",
    "ParseOptions",
]
