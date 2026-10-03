"""Logical Jupyter notebook parsing.

A notebook is JSON, and diffing that JSON directly is noisy: execution counts,
outputs and metadata change on every run.  By default this parser turns a
notebook into a readable sequence of lines::

    ━━ Cell 1 [code] ━━
    import pandas as pd
    ━━ Cell 2 [markdown] ━━
    # Analysis

Only cell *sources* are compared.  ``execution_count``, ``metadata`` and
``outputs`` are ignored unless ``include_output`` is requested, in which case
textual outputs are appended under each code cell as ``[output] ...`` lines.

Cell headers are compared by cell type only (their comparison key omits the
cell number), so inserting one cell does not make every later header look
modified.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List

from differentiater.errors import InvalidNotebookError
from differentiater.models.document import LoadedDocument, ParseOptions
from differentiater.parsers.text import decode_text, normalize_newlines, split_lines

HEADER_TEMPLATE = "━━ Cell {index} [{cell_type}] ━━"
OUTPUT_PREFIX = "[output] "


def load_notebook_document(path: str, data: bytes, options: ParseOptions) -> LoadedDocument:
    """Parse ``.ipynb`` bytes into a logical, cell-by-cell document."""
    text, encoding = decode_text(data, path)
    notebook = _parse_json(text, path)

    lines: List[str] = []
    keys: List[str] = []
    for index, cell in enumerate(notebook["cells"], start=1):
        if not isinstance(cell, dict):
            raise InvalidNotebookError(path, f"cell {index} is not an object")
        cell_type = str(cell.get("cell_type", "unknown"))

        lines.append(HEADER_TEMPLATE.format(index=index, cell_type=cell_type))
        keys.append(f"\x00cell-header[{cell_type}]")

        for line in source_lines(cell.get("source", "")):
            lines.append(line)
            keys.append(line)

        if options.include_output and cell_type == "code":
            for line in output_lines(cell.get("outputs") or []):
                lines.append(OUTPUT_PREFIX + line)
                keys.append(OUTPUT_PREFIX + line)

    return LoadedDocument(
        path=path,
        lines=lines,
        keys=keys,
        has_final_newline=True,
        encoding=encoding,
        line_ending="LF",
        kind="notebook",
    )


def _parse_json(text: str, path: str) -> Dict[str, Any]:
    try:
        notebook = json.loads(text)
    except json.JSONDecodeError as error:
        raise InvalidNotebookError(
            path, f"malformed JSON ({error.msg} at line {error.lineno})"
        ) from None
    if not isinstance(notebook, dict) or not isinstance(notebook.get("cells"), list):
        raise InvalidNotebookError(path, "missing 'cells' list")
    return notebook


def _join(value: Any) -> str:
    """Notebook text fields are either a string or a list of strings."""
    if isinstance(value, list):
        return "".join(str(part) for part in value)
    return "" if value is None else str(value)


def source_lines(source: Any) -> List[str]:
    """Split a cell's ``source`` field into lines."""
    lines, _ = split_lines(normalize_newlines(_join(source)))
    return lines


def output_lines(outputs: Iterable[Any]) -> List[str]:
    """Render the textual content of code-cell outputs as lines."""
    lines: List[str] = []
    for output in outputs:
        if not isinstance(output, dict):
            continue
        output_type = output.get("output_type")
        if output_type == "stream":
            lines.extend(source_lines(output.get("text", "")))
        elif output_type in ("execute_result", "display_data"):
            data = output.get("data") or {}
            if "text/plain" in data:
                lines.extend(source_lines(data["text/plain"]))
            else:
                lines.append("<" + ", ".join(sorted(data)) + ">")
        elif output_type == "error":
            lines.append(f"{output.get('ename', 'Error')}: {output.get('evalue', '')}")
    return lines
