"""Banner, section headers and the summary block."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from differentiater.models.diff_result import DiffResult
from differentiater.renderers.theme import (
    DEFAULT_THEME,
    HEAVY_RULE,
    LIGHT_RULE,
    RULE_WIDTH,
    Theme,
)

LABEL_WIDTH = 13


def render_banner(console: Console, result: DiffResult, theme: Theme = DEFAULT_THEME) -> None:
    """Print the title banner and the names of the compared files."""
    console.print(Text(HEAVY_RULE * RULE_WIDTH, style=theme.rule))
    console.print(Text("DIFFERENTIATER".center(RULE_WIDTH).rstrip(), style=theme.title))
    console.print(Text(HEAVY_RULE * RULE_WIDTH, style=theme.rule))
    console.print()
    console.print(_field("FILE A", result.old.path, theme))
    console.print(_field("FILE B", result.new.path, theme))
    for note in result.notes:
        console.print(_field("NOTE", note, theme, value_style=theme.note))


def render_section_header(console: Console, title: str, theme: Theme = DEFAULT_THEME) -> None:
    """Print a section title framed by light rules."""
    console.print()
    console.print(Text(LIGHT_RULE * RULE_WIDTH, style=theme.rule))
    console.print(Text(title, style=theme.section))
    console.print(Text(LIGHT_RULE * RULE_WIDTH, style=theme.rule))
    console.print()


def render_summary(console: Console, result: DiffResult, theme: Theme = DEFAULT_THEME) -> None:
    """Print the summary statistics computed from the diff operations."""
    summary = result.summary
    render_section_header(console, "SUMMARY", theme)

    console.print(_field("Old Lines", str(summary.old_lines), theme))
    console.print(_field("New Lines", str(summary.new_lines), theme))
    console.print(_field("Line Delta", f"{summary.line_delta:+d}", theme))
    console.print()
    console.print(_field("Inserted", str(summary.inserted), theme, value_style=theme.insertion))
    console.print(_field("Deleted", str(summary.deleted), theme, value_style=theme.deletion))
    console.print(_field("Modified", str(summary.modified), theme, value_style=theme.modification))
    console.print(_field("Unchanged", str(summary.unchanged), theme))
    if summary.modified:
        console.print()
        console.print(_field("Chars Added", str(summary.chars_inserted), theme))
        console.print(_field("Chars Removed", str(summary.chars_deleted), theme))
    console.print()
    console.print(_field("Total Changes", str(summary.total_changes), theme, label_style=theme.label))
    console.print(Text(HEAVY_RULE * RULE_WIDTH, style=theme.rule))

    if summary.is_identical:
        console.print()
        console.print(Text("Files are identical.", style=theme.success))


def _field(
    label: str,
    value: str,
    theme: Theme,
    *,
    value_style: str = "",
    label_style: str = "",
) -> Text:
    text = Text(f"{label:<{LABEL_WIDTH}}: ", style=label_style)
    text.append(value, style=value_style)
    return text
