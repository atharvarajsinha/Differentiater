"""Semantic styles and symbols used by the terminal renderer.

Renderers refer only to the *meaning* of a piece of output (``insertion``,
``line_number``, ...).  Changing the look of Differentiater means changing
this file, nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console


@dataclass(frozen=True)
class Theme:
    """Rich style strings keyed by meaning."""

    insertion: str = "green"
    deletion: str = "red"
    modification: str = "yellow"
    unchanged: str = ""
    line_number: str = "dim"
    inserted_text: str = "bold black on green"
    deleted_text: str = "bold white on red"
    marker: str = "bold yellow"
    title: str = "bold cyan"
    section: str = "bold"
    rule: str = "dim"
    label: str = "bold"
    collapsed: str = "dim italic"
    note: str = "dim"
    success: str = "bold green"


DEFAULT_THEME = Theme()

# Symbols (not colors) -- these stay visible with --no-color.
SIGN_INSERT = "+"
SIGN_DELETE = "-"
SIGN_EQUAL = " "
LABEL_INSERT = "+ INSERTION"
LABEL_DELETE = "- DELETION"
LABEL_MODIFY = "~ MODIFICATION"
MARKER_CHAR = "^"
GUTTER_SEPARATOR = " | "
RULE_WIDTH = 60
HEAVY_RULE = "═"
LIGHT_RULE = "─"
NO_NEWLINE_NOTE = "\\ No newline at end of file"


def make_console(*, no_color: bool = False, force_color: bool = False) -> Console:
    """Create the console used for terminal output.

    ``no_color`` disables every ANSI escape sequence (colors *and* bold/dim).
    ``soft_wrap`` keeps long lines intact so character markers stay aligned.
    """
    return Console(
        no_color=no_color,
        color_system=None if no_color else ("truecolor" if force_color else "auto"),
        force_terminal=True if force_color and not no_color else None,
        highlight=False,
        markup=False,
        emoji=False,
        soft_wrap=True,
    )
