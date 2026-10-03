"""Comparison normalisation: build the keys Myers actually compares.

Normalisation never touches the display text or the files on disk.  It
produces a parallel list of *comparison keys* (and the original line number of
each kept line) so that options such as ``--ignore-space`` only change what
counts as "equal".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable, List, Optional, Sequence

from differentiater.models.document import CompareOptions

#: Appended to the key of a final line that has no terminating newline, so
#: that "x" and "x\n" compare as different (like ``\ No newline at end of file``).
NO_EOL_MARKER = "\x00<no newline at end of file>"


@dataclass
class PreparedLines:
    """Lines ready for the line diff."""

    texts: List[str]
    keys: List[Hashable]
    numbers: List[int]


def prepare_lines(
    lines: Sequence[str],
    keys: Optional[Sequence[str]] = None,
    *,
    has_final_newline: bool = True,
    options: Optional[CompareOptions] = None,
) -> PreparedLines:
    """Build comparison keys for ``lines`` according to ``options``."""
    options = options or CompareOptions()
    texts = list(lines)
    comparison = list(keys) if keys is not None else list(texts)

    if options.ignore_space:
        comparison = [_strip_whitespace(key) for key in comparison]
    if texts and not has_final_newline:
        comparison[-1] = comparison[-1] + NO_EOL_MARKER

    numbers = list(range(1, len(texts) + 1))
    if options.ignore_blank_lines:
        kept = [i for i, text in enumerate(texts) if text.strip()]
        texts = [texts[i] for i in kept]
        comparison = [comparison[i] for i in kept]
        numbers = [numbers[i] for i in kept]

    return PreparedLines(texts=texts, keys=comparison, numbers=numbers)


def _strip_whitespace(text: str) -> str:
    """Remove every whitespace character (like ``diff -w``)."""
    return "".join(text.split())
