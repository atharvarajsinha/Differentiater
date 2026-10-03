"""Tests for text loading: encodings, newlines and binary detection."""

import codecs

import pytest

from differentiater.errors import BinaryFileError, InputFileNotFoundError, NotAFileError
from differentiater.parsers import load_document
from differentiater.parsers.text import detect_line_ending, split_lines


def load_bytes(tmp_path, data, name="f.txt"):
    path = tmp_path / name
    path.write_bytes(data)
    return load_document(str(path))


@pytest.mark.parametrize("data", [b"a\nb\n", b"a\r\nb\r\n", b"a\rb\r"])
def test_line_endings_are_normalised(tmp_path, data):
    doc = load_bytes(tmp_path, data)
    assert doc.lines == ["a", "b"] and doc.has_final_newline


def test_line_ending_detection():
    assert detect_line_ending("a\nb\n") == "LF"
    assert detect_line_ending("a\r\nb\r\n") == "CRLF"
    assert detect_line_ending("a\rb") == "CR"
    assert detect_line_ending("a\r\nb\n") == "mixed"
    assert detect_line_ending("abc") == "none"


def test_missing_final_newline(tmp_path):
    doc = load_bytes(tmp_path, b"a\nb")
    assert doc.lines == ["a", "b"] and not doc.has_final_newline


def test_empty_file(tmp_path):
    doc = load_bytes(tmp_path, b"")
    assert doc.lines == [] and doc.has_final_newline


def test_split_lines_keeps_blank_and_whitespace_lines():
    assert split_lines("\n") == ([""], True)
    assert split_lines("a  \n\t\n\n") == (["a  ", "\t", ""], True)
    # Form feed / Unicode line separators are content, not line breaks.
    assert split_lines("a\x0cb c") == (["a\x0cb c"], False)


def test_utf8_bom(tmp_path):
    doc = load_bytes(tmp_path, codecs.BOM_UTF8 + "héllo\n".encode())
    assert doc.lines == ["héllo"] and doc.encoding == "utf-8-sig"


def test_utf16_with_bom(tmp_path):
    doc = load_bytes(tmp_path, "hi\nthere\n".encode("utf-16"))
    assert doc.lines == ["hi", "there"]


def test_unicode_hindi_and_emoji(tmp_path):
    doc = load_bytes(tmp_path, "नमस्ते दुनिया\n😀 🎉\n".encode())
    assert doc.lines == ["नमस्ते दुनिया", "😀 🎉"]


def test_latin1_fallback(tmp_path):
    doc = load_bytes(tmp_path, "café\n".encode("latin-1"))
    assert doc.lines == ["café"] and doc.encoding == "latin-1"


def test_binary_detection(tmp_path):
    with pytest.raises(BinaryFileError):
        load_bytes(tmp_path, b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", "img.png")


def test_missing_file(tmp_path):
    with pytest.raises(InputFileNotFoundError, match="file not found"):
        load_document(str(tmp_path / "missing.py"))


def test_directory_is_rejected(tmp_path):
    with pytest.raises(NotAFileError):
        load_document(str(tmp_path))


def test_files_are_not_modified(tmp_path):
    path = tmp_path / "f.txt"
    original = b"a\r\nb  \r\n"
    path.write_bytes(original)
    load_document(str(path))
    assert path.read_bytes() == original
