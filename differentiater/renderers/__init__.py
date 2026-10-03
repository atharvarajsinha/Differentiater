"""Output renderers.  None of them compute diffs; they only present results."""

from differentiater.renderers.json_renderer import build_payload, render_json
from differentiater.renderers.terminal import TerminalRenderer
from differentiater.renderers.theme import DEFAULT_THEME, Theme, make_console

__all__ = [
    "DEFAULT_THEME",
    "TerminalRenderer",
    "Theme",
    "build_payload",
    "make_console",
    "render_json",
]
