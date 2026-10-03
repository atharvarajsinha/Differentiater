"""Human-readable terminal output (Part A, Part B) built with ``rich``.

The renderer consumes a :class:`DiffResult` and never computes diffs itself:
character highlighting comes from the Myers character operations stored on
each MODIFY operation.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

from rich.cells import cell_len
from rich.console import Console
from rich.text import Text

from differentiater.models.diff_result import (
    CharacterOperation,
    DiffOperation,
    DiffResult,
    OperationType,
)
from differentiater.renderers.summary import (
    render_banner,
    render_section_header,
    render_summary,
)
from differentiater.renderers.theme import (
    DEFAULT_THEME,
    GUTTER_SEPARATOR,
    LABEL_DELETE,
    LABEL_INSERT,
    LABEL_MODIFY,
    MARKER_CHAR,
    NO_NEWLINE_NOTE,
    SIGN_DELETE,
    SIGN_EQUAL,
    SIGN_INSERT,
    Theme,
)

DEFAULT_CONTEXT = 3
TAB_WIDTH = 4
PART_A_TITLE = "PART A — LINE DIFF"
PART_B_TITLE = "PART B — CHARACTER DIFF"

_LABELS = {
    OperationType.INSERT: LABEL_INSERT,
    OperationType.DELETE: LABEL_DELETE,
    OperationType.MODIFY: LABEL_MODIFY,
}


def visible(text: str) -> str:
    """Make text safe and predictable to print.

    Tabs become spaces (so markers line up) and other control characters are
    shown escaped instead of being sent raw to the terminal.
    """
    if text.isprintable():
        return text
    pieces = []
    for char in text:
        if char == "\t":
            pieces.append(" " * TAB_WIDTH)
        elif not char.isprintable() and char != " " and ord(char) < 0xA0:
            pieces.append(f"\\x{ord(char):02x}")
        else:
            pieces.append(char)
    return "".join(pieces)


class TerminalRenderer:
    """Render a diff result for people."""

    def __init__(
        self,
        console: Console,
        theme: Theme = DEFAULT_THEME,
        context: int = DEFAULT_CONTEXT,
    ) -> None:
        self.console = console
        self.theme = theme
        self.context = context

    # ------------------------------------------------------------------ API

    def render(
        self,
        result: DiffResult,
        *,
        show_summary: bool = True,
        parts: Sequence[str] = ("A", "B"),
    ) -> None:
        """Render the requested sections in order: summary, Part A, Part B."""
        if show_summary:
            render_banner(self.console, result, self.theme)
            render_summary(self.console, result, self.theme)
        if "A" in parts:
            self.render_part_a(result)
        if "B" in parts:
            self.render_part_b(result)

    def render_part_a(self, result: DiffResult) -> None:
        """Line-level diff with context lines and collapsed unchanged blocks."""
        render_section_header(self.console, PART_A_TITLE, self.theme)
        if not result.has_differences:
            self._print_no_differences()
            return

        operations = result.operations
        width = _number_width(result)
        ranges = visible_ranges(operations, self.context)

        previous_end = -1
        for start, end in ranges:
            hidden = start - previous_end - 1
            if hidden > 0:
                self._print_collapsed(hidden, width, leading=previous_end < 0)
            self._print_block(result, operations[start:end + 1], width)
            previous_end = end
        trailing = len(operations) - previous_end - 1
        if trailing > 0:
            self._print_collapsed(trailing, width, leading=False)

    def render_part_b(self, result: DiffResult) -> None:
        """Every change, with character-level highlighting for modifications."""
        render_section_header(self.console, PART_B_TITLE, self.theme)
        if not result.has_differences:
            self._print_no_differences()
            return

        width = _number_width(result)
        first = True
        for group in group_changes(result.operations):
            if not first:
                self.console.print()
            first = False
            kind = group[0].operation
            self.console.print(Text(_LABELS[kind], style=self._style_for(kind)))
            self.console.print()
            for op in group:
                if kind == OperationType.MODIFY:
                    self._print_character_diff(result, op, width)
                else:
                    self._print_line(result, op, width)

    # ------------------------------------------------------------ Part A

    def _print_block(self, result: DiffResult, block: Sequence[DiffOperation], width: int) -> None:
        previous_kind: Optional[OperationType] = None
        for op in block:
            kind = op.operation
            starts_group = kind != OperationType.EQUAL and (
                kind != previous_kind or kind == OperationType.MODIFY
            )
            if starts_group:
                self.console.print()
                self.console.print(Text(_LABELS[kind], style=self._style_for(kind)))
                self.console.print()
            elif kind == OperationType.EQUAL and previous_kind not in (None, OperationType.EQUAL):
                self.console.print()
            self._print_line(result, op, width)
            previous_kind = kind

    def _print_line(self, result: DiffResult, op: DiffOperation, width: int) -> None:
        """Print one operation as plain (whole-line colored) diff lines."""
        if op.operation in (OperationType.DELETE, OperationType.MODIFY):
            self._print_row(SIGN_DELETE, op.old_line_number, None, op.old_text,
                            self.theme.deletion, width)
            self._print_eol_note(result, op, old_side=True)
        if op.operation in (OperationType.INSERT, OperationType.MODIFY):
            self._print_row(SIGN_INSERT, None, op.new_line_number, op.new_text,
                            self.theme.insertion, width)
            self._print_eol_note(result, op, old_side=False)
        if op.operation == OperationType.EQUAL:
            self._print_row(SIGN_EQUAL, op.old_line_number, op.new_line_number, op.new_text,
                            self.theme.unchanged, width)
            self._print_eol_note(result, op, old_side=False)

    def _print_row(
        self,
        sign: str,
        old_number: Optional[int],
        new_number: Optional[int],
        text: Optional[str],
        style: str,
        width: int,
    ) -> None:
        row = self._gutter(sign, old_number, new_number, width, style)
        row.append(visible(text or ""), style=style)
        self.console.print(row)

    # ------------------------------------------------------------ Part B

    def _print_character_diff(self, result: DiffResult, op: DiffOperation, width: int) -> None:
        char_ops = op.char_operations or []
        self._print_highlighted(op.old_line_number, char_ops, width, old_side=True)
        self._print_eol_note(result, op, old_side=True)
        self._print_highlighted(op.new_line_number, char_ops, width, old_side=False)
        self._print_eol_note(result, op, old_side=False)

    def _print_highlighted(
        self,
        number: Optional[int],
        char_ops: Sequence[CharacterOperation],
        width: int,
        *,
        old_side: bool,
    ) -> None:
        """Print one side of a modified line with changed runs highlighted,
        followed by a ``^`` marker row under the changed characters."""
        old_number, new_number = (number, None) if old_side else (None, number)
        if old_side:
            sign, skip, changed = SIGN_DELETE, OperationType.INSERT, OperationType.DELETE
            base_style, changed_style = self.theme.deletion, self.theme.deleted_text
        else:
            sign, skip, changed = SIGN_INSERT, OperationType.DELETE, OperationType.INSERT
            base_style, changed_style = self.theme.insertion, self.theme.inserted_text

        row = self._gutter(sign, old_number, new_number, width, base_style)
        for c in char_ops:
            if c.operation != skip:
                row.append(visible(c.text), style=changed_style if c.operation == changed else base_style)
        self.console.print(row)

        marker_line = character_markers(char_ops, old_side=old_side)
        if marker_line:
            padding = " " * cell_len(self._gutter(sign, old_number, new_number, width, "").plain)
            self.console.print(Text(padding + marker_line, style=self.theme.marker))

    # ------------------------------------------------------------ helpers

    def _gutter(
        self,
        sign: str,
        old_number: Optional[int],
        new_number: Optional[int],
        width: int,
        style: str,
    ) -> Text:
        """``<sign> <old line> <new line> | `` -- a blank column means the line
        does not exist on that side."""
        old = "" if old_number is None else old_number
        new = "" if new_number is None else new_number
        gutter = Text(f"{sign} ", style=style)
        gutter.append(f"{old:>{width}} {new:>{width}}", style=self.theme.line_number)
        gutter.append(GUTTER_SEPARATOR, style=self.theme.line_number)
        return gutter

    def _print_collapsed(self, count: int, width: int, *, leading: bool) -> None:
        indent = " " * (2 * width + 4)
        noun = "line" if count == 1 else "lines"
        style = self.theme.collapsed
        if not leading:
            self.console.print(Text(f"{indent}│", style=style))
        self.console.print(Text(f"{indent}│ {count} unchanged {noun}", style=style))
        self.console.print(Text(f"{indent}│", style=style))

    def _print_eol_note(self, result: DiffResult, op: DiffOperation, *, old_side: bool) -> None:
        info = result.old if old_side else result.new
        number = op.old_line_number if old_side else op.new_line_number
        if not info.has_final_newline and number == info.line_count and number is not None:
            self.console.print(Text(NO_NEWLINE_NOTE, style=self.theme.note))

    def _print_no_differences(self) -> None:
        self.console.print(Text("No differences found.", style=self.theme.success))

    def _style_for(self, kind: OperationType) -> str:
        return {
            OperationType.INSERT: self.theme.insertion,
            OperationType.DELETE: self.theme.deletion,
            OperationType.MODIFY: self.theme.modification,
        }.get(kind, self.theme.unchanged)


# ---------------------------------------------------------------- layout


def visible_ranges(operations: Sequence[DiffOperation], context: int) -> List[Tuple[int, int]]:
    """Inclusive index ranges of operations to show with ``context`` lines.

    When context is positive, ranges separated by a single hidden line are
    merged: collapsing one line would take more space than showing it.
    """
    ranges: List[Tuple[int, int]] = []
    last = len(operations) - 1
    # With --context 0 the user asked for changed lines only: never pad.
    merge_gap = 2 if context > 0 else 1
    for index, op in enumerate(operations):
        if not op.is_change:
            continue
        start, end = max(0, index - context), min(last, index + context)
        if ranges and start <= ranges[-1][1] + merge_gap:
            ranges[-1] = (ranges[-1][0], max(ranges[-1][1], end))
        else:
            ranges.append((start, end))
    # The same rule at the file edges: show a lone leading/trailing line.
    if context > 0 and ranges and ranges[0][0] == 1:
        ranges[0] = (0, ranges[0][1])
    if context > 0 and ranges and ranges[-1][1] == last - 1:
        ranges[-1] = (ranges[-1][0], last)
    return ranges


def group_changes(operations: Iterable[DiffOperation]) -> List[List[DiffOperation]]:
    """Group consecutive changes of the same kind; each MODIFY is its own group."""
    groups: List[List[DiffOperation]] = []
    previous: Optional[DiffOperation] = None
    for op in operations:
        if not op.is_change:
            previous = None
            continue
        same_group = (
            previous is not None
            and previous.operation == op.operation
            and op.operation != OperationType.MODIFY
        )
        if same_group:
            groups[-1].append(op)
        else:
            groups.append([op])
        previous = op
    return groups


def character_markers(char_ops: Sequence[CharacterOperation], *, old_side: bool) -> str:
    """The ``^`` marker row for one side of a modified line (no gutter)."""
    skip = OperationType.INSERT if old_side else OperationType.DELETE
    changed = OperationType.DELETE if old_side else OperationType.INSERT
    pieces = [
        (MARKER_CHAR if c.operation == changed else " ") * cell_len(visible(c.text))
        for c in char_ops
        if c.operation != skip
    ]
    return "".join(pieces).rstrip()


def _number_width(result: DiffResult) -> int:
    return len(str(max(result.old.line_count, result.new.line_count, 1)))
