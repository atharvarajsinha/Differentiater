"""End-to-end tests of the command-line interface."""

import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from differentiater import __version__
from differentiater.cli import main
from differentiater.core.line_diff import diff_lines
from differentiater.engine import compare_files
from differentiater.renderers.terminal import TerminalRenderer, visible_ranges
from differentiater.renderers.theme import make_console

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
ANSI = re.compile(r"\x1b\[[0-9;]*m")


@pytest.fixture
def files(tmp_path):
    def make(old, new, suffix=".py"):
        a, b = tmp_path / f"old{suffix}", tmp_path / f"new{suffix}"
        a.write_text(old, encoding="utf-8", newline="")
        b.write_text(new, encoding="utf-8", newline="")
        return str(a), str(b)
    return make


def run(capsys, *argv):
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def test_exit_code_0_for_identical_files(capsys, files):
    a, b = files("x = 1\n", "x = 1\n")
    code, out, _ = run(capsys, a, b)
    assert code == 0 and "Files are identical." in out


def test_exit_code_1_for_different_files(capsys, files):
    code, _, _ = run(capsys, *files("x = 1\n", "x = 2\n"))
    assert code == 1


def test_exit_code_2_and_message_for_missing_file(capsys, files):
    _, b = files("", "")
    code, out, err = run(capsys, "missing.py", b)
    assert code == 2 and out == ""
    assert err.strip() == "Error: file not found: missing.py"


def test_exit_code_2_for_bad_usage(capsys):
    assert run(capsys, "only_one_file.py")[0] == 2
    assert run(capsys, "a", "b", "--part", "C")[0] == 2
    assert run(capsys, "a", "b", "--context", "-1")[0] == 2


def test_binary_file_error(capsys, tmp_path, files):
    binary = tmp_path / "data.bin"
    binary.write_bytes(b"\x00\x01\x02\x03")
    code, _, err = run(capsys, str(binary), files("", "")[1])
    assert code == 2
    assert err.strip() == "Error: binary files are not supported for text diff."


def test_version(capsys):
    code, out, _ = run(capsys, "--version")
    assert code == 0 and __version__ in out


def test_default_output_has_summary_and_both_parts(capsys, files):
    code, out, _ = run(capsys, *files("a\nreturn a + b\nc\n", "a\nreturn a + b + c\nc\n"))
    assert code == 1
    for heading in ("DIFFERENTIATER", "SUMMARY", "PART A — LINE DIFF", "PART B — CHARACTER DIFF"):
        assert heading in out
    assert re.search(r"Modified\s*: 1", out)


def test_part_a_only(capsys, files):
    _, out, _ = run(capsys, *files("x = 10\n", "x = 20\nprint(x)\n"), "--part", "A")
    assert "PART A" in out and "PART B" not in out and "SUMMARY" not in out
    assert "~ MODIFICATION" in out and "+ INSERTION" in out
    assert "- 1   | x = 10" in out and "+   1 | x = 20" in out


def test_part_b_character_markers(capsys, files):
    _, out, _ = run(capsys, *files('username = "Atharva"\n', 'username = "Atharva K"\n'),
                    "--part", "b", "--no-color")
    assert "PART A" not in out
    lines = out.splitlines()
    new_row = next(i for i, line in enumerate(lines) if line.startswith("+"))
    marker = lines[new_row + 1]
    # The ^ markers sit exactly under the inserted " K".
    assert marker.index("^") == lines[new_row].index(" K")
    assert marker.strip() == "^^"


def test_summary_only(capsys, files):
    _, out, _ = run(capsys, *files("a\n", "b\n"), "--summary")
    assert "SUMMARY" in out and "PART A" not in out and "PART B" not in out


def test_json_output(capsys, files):
    code, out, _ = run(capsys, *files("keep\nreturn a + b\n", "keep\nreturn a + b + c\nnew\n"), "--json")
    assert code == 1
    data = json.loads(out)
    assert data["summary"]["modified"] == 1 and data["summary"]["inserted"] == 1
    modify = next(op for op in data["operations"] if op["type"] == "modify")
    assert modify["old_line"] == 2 and modify["new_line"] == 2
    assert modify["character_diff"] == [
        {"type": "equal", "text": "return a + b"},
        {"type": "insert", "text": " + c"},
    ]
    insert = next(op for op in data["operations"] if op["type"] == "insert")
    assert insert["old_line"] is None and insert["new_text"] == "new"


def test_json_identical_exit_code(capsys, files):
    code, out, _ = run(capsys, *files("same\n", "same\n"), "--json")
    assert code == 0 and json.loads(out)["identical"] is True


def test_no_color_has_no_ansi(capsys, files):
    _, out, _ = run(capsys, *files("a\n", "b\n"), "--no-color")
    assert not ANSI.search(out)


def test_color_renderer_emits_ansi_and_no_color_does_not(files):
    result = compare_files(*files("return a + b\n", "return a + b + c\n"))
    colored = make_console(force_color=True)
    plain = make_console(no_color=True)
    for console in (colored, plain):
        console.file = io.StringIO()
        TerminalRenderer(console).render(result)
    assert ANSI.search(colored.file.getvalue())
    assert not ANSI.search(plain.file.getvalue())


def test_context_option_collapses_unchanged_lines(capsys, files):
    old = "".join(f"line {i}\n" for i in range(1, 31))
    new = old.replace("line 15\n", "line fifteen\n")
    _, out3, _ = run(capsys, *files(old, new), "--part", "A")
    assert "line 12" in out3 and "line 11" not in out3
    assert "11 unchanged lines" in out3 and "12 unchanged lines" in out3
    _, out0, _ = run(capsys, *files(old, new), "--part", "A", "--context", "0")
    assert "line 14" not in out0 and "line 16" not in out0
    _, out5, _ = run(capsys, *files(old, new), "--part", "A", "--context", "5")
    assert "line 10" in out5 and "line 9 " not in out5


def test_visible_ranges_merges_nearby_changes():
    old = [f"line {i}" for i in range(10)]
    new = list(old)
    new[1], new[8] = "line one", "line eight"
    ops = diff_lines(old, new)  # changes at operation indices 1 and 8
    assert visible_ranges(ops, 1) == [(0, 2), (7, 9)]
    assert visible_ranges(ops, 0) == [(1, 1), (8, 8)]
    assert visible_ranges(ops, 3) == [(0, 9)]


def test_no_newline_marker(capsys, files):
    _, out, _ = run(capsys, *files("a\nb", "a\nb\n"), "--part", "A")
    assert "\\ No newline at end of file" in out


def test_crlf_vs_lf_content_is_equal(capsys, files):
    code, out, _ = run(capsys, *files("a\r\nb\r\n", "a\nb\n"))
    assert code == 0 and "line endings differ" in out


def test_ignore_options(capsys, files):
    a, b = files("x = 1\n\ny=2\n", "x  =  1\ny = 2\n")
    assert run(capsys, a, b)[0] == 1
    assert run(capsys, a, b, "--ignore-space", "--ignore-blank-lines")[0] == 0
    assert run(capsys, a, b, "--ignore-space")[0] == 1


def test_unicode_output(capsys, files):
    code, out, _ = run(capsys, *files("नमस्ते\n", "नमस्ते दुनिया 🌍\n"), "--part", "B")
    assert code == 1 and "नमस्ते दुनिया 🌍" in out


def test_control_characters_are_escaped(capsys, files):
    _, out, _ = run(capsys, *files("a\n", "a\x1b[31mred\n"), "--no-color", "--part", "A")
    assert "\x1b" not in out and "\\x1b[31mred" in out


@pytest.mark.parametrize("stem", ["py", "java", "txt", "json", "js", "cpp", "sql", "md", "ipynb"])
def test_example_files(capsys, stem):
    old, new = EXAMPLES / f"old.{stem}", EXAMPLES / f"new.{stem}"
    code, out, err = run(capsys, str(old), str(new), "--no-color")
    assert code == 1 and err == "" and "PART B" in out
    code, out, _ = run(capsys, str(old), str(old))
    assert code == 0


def test_legacy_output_encoding_does_not_crash(files):
    # Regression: Windows redirects default to cp1252, which cannot encode the
    # box-drawing characters, Hindi or emoji.  The CLI must switch to UTF-8.
    a, b = files("नमस्ते\n", "नमस्ते 😀\n", suffix=".txt")
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    proc = subprocess.run(
        [sys.executable, "-m", "differentiater", a, b, "--no-color"],
        capture_output=True, env=env,
    )
    assert proc.returncode == 1
    assert b"Traceback" not in proc.stderr
    assert "नमस्ते 😀" in proc.stdout.decode("utf-8")


def test_notebook_flags(capsys):
    old, new = str(EXAMPLES / "old.ipynb"), str(EXAMPLES / "new.ipynb")
    logical = json.loads(run(capsys, old, new, "--json")[1])
    with_output = json.loads(run(capsys, old, new, "--json", "--include-output")[1])
    raw = json.loads(run(capsys, old, new, "--json", "--raw")[1])
    assert logical["files"]["a"]["kind"] == "notebook"
    assert raw["files"]["a"]["kind"] == "text"
    assert with_output["summary"]["total_changes"] > logical["summary"]["total_changes"]
    assert raw["summary"]["total_changes"] > logical["summary"]["total_changes"]
