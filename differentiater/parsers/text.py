"""Plain-text loading: binary detection, decoding and newline normalisation."""

from __future__ import annotations

import codecs
from pathlib import Path
from typing import List, Tuple

from differentiater.errors import (
    BinaryFileError,
    FileReadError,
    InputFileNotFoundError,
    NotAFileError,
)
from differentiater.models.document import LoadedDocument, ParseOptions

#: How many leading bytes are inspected for binary detection.
BINARY_SNIFF_BYTES = 8192

#: Share of control bytes above which a file is treated as binary.
BINARY_CONTROL_RATIO = 0.30

_TEXT_CONTROL_BYTES = {0x08, 0x09, 0x0A, 0x0C, 0x0D, 0x1B}

_UNICODE_BOMS = (
    (codecs.BOM_UTF32_LE, "utf-32"),
    (codecs.BOM_UTF32_BE, "utf-32"),
    (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF16_LE, "utf-16"),
    (codecs.BOM_UTF16_BE, "utf-16"),
)


def read_bytes(path: str) -> bytes:
    """Read a file's bytes, translating OS errors into clean CLI errors."""
    file_path = Path(path)
    if not file_path.exists():
        raise InputFileNotFoundError(path)
    if not file_path.is_file():
        raise NotAFileError(path)
    try:
        return file_path.read_bytes()
    except PermissionError:
        raise FileReadError(path, "permission denied") from None
    except OSError as error:
        raise FileReadError(path, error.strerror or str(error)) from None


def decode_text(data: bytes, path: str) -> Tuple[str, str]:
    """Decode bytes to text, returning ``(text, encoding)``.

    UTF-8 (with or without BOM) is the primary encoding; UTF-16/32 are
    accepted when they carry a BOM.  Undecodable non-binary data falls back
    to Latin-1, which never fails.

    Raises:
        BinaryFileError: if the data looks binary.
    """
    for bom, encoding in _UNICODE_BOMS:
        if data.startswith(bom):
            try:
                return data.decode(encoding), encoding
            except UnicodeDecodeError:
                raise BinaryFileError(path) from None
    if is_probably_binary(data):
        raise BinaryFileError(path)
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("latin-1"), "latin-1"


def is_probably_binary(data: bytes) -> bool:
    """Heuristic: NUL bytes or many control characters mean binary."""
    sample = data[:BINARY_SNIFF_BYTES]
    if not sample:
        return False
    if b"\x00" in sample:
        return True
    control = sum(1 for byte in sample if byte < 0x20 and byte not in _TEXT_CONTROL_BYTES)
    return control / len(sample) > BINARY_CONTROL_RATIO


def detect_line_ending(text: str) -> str:
    """Name the line-ending convention used by ``text``."""
    crlf = text.count("\r\n")
    cr = text.count("\r") - crlf
    lf = text.count("\n") - crlf
    present = [name for name, count in (("CRLF", crlf), ("LF", lf), ("CR", cr)) if count]
    if not present:
        return "none"
    return present[0] if len(present) == 1 else "mixed"


def normalize_newlines(text: str) -> str:
    """Convert CRLF and lone CR line endings to LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def split_lines(text: str) -> Tuple[List[str], bool]:
    """Split normalised text into lines.

    Returns ``(lines, has_final_newline)``.  Only ``\\n`` separates lines --
    unlike :meth:`str.splitlines`, form feeds or Unicode line separators
    inside a line are preserved.  An empty file has no lines and counts as
    newline-terminated.
    """
    if not text:
        return [], True
    has_final_newline = text.endswith("\n")
    if has_final_newline:
        text = text[:-1]
    return text.split("\n"), has_final_newline


def load_text_document(path: str, data: bytes, options: ParseOptions) -> LoadedDocument:
    """Parser for ordinary text files (the default parser)."""
    text, encoding = decode_text(data, path)
    line_ending = detect_line_ending(text)
    lines, has_final_newline = split_lines(normalize_newlines(text))
    return LoadedDocument(
        path=path,
        lines=lines,
        has_final_newline=has_final_newline,
        encoding=encoding,
        line_ending=line_ending,
        kind="text",
    )
