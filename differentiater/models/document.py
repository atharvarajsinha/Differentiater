"""Parsed input documents and comparison options."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LoadedDocument:
    """A file turned into a sequence of lines ready for comparison.

    Attributes:
        path: The path as given by the user (used for display).
        lines: Display text of each line, without line terminators.
        keys: Optional comparison keys, one per line.  Parsers use these when
            the text shown to the user should not take part in matching
            verbatim (e.g. notebook cell headers that contain a cell number).
            ``None`` means "compare the lines themselves".
        has_final_newline: Whether the file ended with a line terminator.
        encoding: The encoding the bytes were decoded with.
        line_ending: ``"LF"``, ``"CRLF"``, ``"CR"``, ``"mixed"`` or ``"none"``.
        kind: ``"text"``, ``"notebook"`` or another parser-specific label.
    """

    path: str
    lines: List[str]
    keys: Optional[List[str]] = None
    has_final_newline: bool = True
    encoding: str = "utf-8"
    line_ending: str = "LF"
    kind: str = "text"


@dataclass(frozen=True)
class ParseOptions:
    """Options that control how files are turned into lines."""

    raw: bool = False
    include_output: bool = False


@dataclass(frozen=True)
class CompareOptions:
    """Options that only affect how lines are *compared*, never the files."""

    ignore_space: bool = False
    ignore_blank_lines: bool = False
