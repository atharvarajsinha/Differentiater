"""File loading and the parser registry.

Parsers are selected by file extension.  To support a new format, write a
function ``(path, data, options) -> LoadedDocument`` and register it::

    register_parser(".csv", load_csv_document)

Files without a registered parser (and every file under ``--raw``) are read
as plain text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Optional

from differentiater.models.document import LoadedDocument, ParseOptions
from differentiater.parsers.notebook import load_notebook_document
from differentiater.parsers.text import load_text_document, read_bytes

Parser = Callable[[str, bytes, ParseOptions], LoadedDocument]

_PARSERS: Dict[str, Parser] = {}


def register_parser(suffix: str, parser: Parser) -> None:
    """Register ``parser`` for files ending in ``suffix`` (e.g. ``".ipynb"``)."""
    _PARSERS[suffix.lower()] = parser


def parser_for(path: str, options: ParseOptions) -> Parser:
    """Pick the parser for ``path``; raw mode always uses plain text."""
    if options.raw:
        return load_text_document
    return _PARSERS.get(Path(path).suffix.lower(), load_text_document)


def load_document(path: str, options: Optional[ParseOptions] = None) -> LoadedDocument:
    """Read ``path`` from disk and parse it.  The file is never modified."""
    options = options or ParseOptions()
    data = read_bytes(path)
    return parser_for(path, options)(path, data, options)


register_parser(".ipynb", load_notebook_document)

__all__ = ["load_document", "parser_for", "register_parser"]
