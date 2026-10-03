"""Tests for logical Jupyter notebook comparison."""

import copy
import json

import pytest

from differentiater.engine import compare_files
from differentiater.errors import InvalidNotebookError
from differentiater.models.document import ParseOptions
from differentiater.parsers import load_document

BASE = {
    "cells": [
        {"cell_type": "markdown", "metadata": {}, "source": ["# Title\n", "Intro text"]},
        {
            "cell_type": "code",
            "execution_count": 1,
            "metadata": {},
            "outputs": [{"output_type": "stream", "name": "stdout", "text": ["3\n"]}],
            "source": ["x = 1\n", "y = 2\n", "print(x + y)"],
        },
    ],
    "metadata": {"kernelspec": {"name": "python3"}},
    "nbformat": 4,
    "nbformat_minor": 5,
}


def write(tmp_path, name, notebook):
    path = tmp_path / name
    path.write_text(json.dumps(notebook), encoding="utf-8")
    return str(path)


def compare(tmp_path, old, new, **options):
    return compare_files(
        write(tmp_path, "old.ipynb", old),
        write(tmp_path, "new.ipynb", new),
        parse_options=ParseOptions(**options),
    )


def test_logical_view(tmp_path):
    doc = load_document(write(tmp_path, "n.ipynb", BASE))
    assert doc.kind == "notebook"
    assert doc.lines == [
        "━━ Cell 1 [markdown] ━━", "# Title", "Intro text",
        "━━ Cell 2 [code] ━━", "x = 1", "y = 2", "print(x + y)",
    ]


def test_same_notebook(tmp_path):
    assert not compare(tmp_path, BASE, BASE).has_differences


def test_changed_code_cell(tmp_path):
    new = copy.deepcopy(BASE)
    new["cells"][1]["source"][1] = "y = 20\n"
    result = compare(tmp_path, BASE, new)
    assert result.summary.modified == 1
    change = result.changes[0]
    assert (change.old_text, change.new_text) == ("y = 2", "y = 20")


def test_changed_markdown_cell(tmp_path):
    new = copy.deepcopy(BASE)
    new["cells"][0]["source"] = ["# New Title\n", "Intro text"]
    result = compare(tmp_path, BASE, new)
    assert result.summary.modified == 1 and result.summary.total_changes == 1


def test_added_cell(tmp_path):
    new = copy.deepcopy(BASE)
    new["cells"].insert(0, {"cell_type": "code", "metadata": {}, "outputs": [],
                            "source": "import os"})
    result = compare(tmp_path, BASE, new)
    # Header + one source line inserted; renumbered headers are NOT changes.
    assert result.summary.inserted == 2
    assert result.summary.modified == 0 and result.summary.deleted == 0


def test_deleted_cell(tmp_path):
    new = copy.deepcopy(BASE)
    del new["cells"][0]
    result = compare(tmp_path, BASE, new)
    assert result.summary.deleted == 3 and result.summary.inserted == 0


def test_metadata_only_change_is_ignored(tmp_path):
    new = copy.deepcopy(BASE)
    new["metadata"]["widgets"] = {"state": {}}
    new["cells"][1]["metadata"] = {"collapsed": True}
    new["cells"][1]["execution_count"] = 42
    assert not compare(tmp_path, BASE, new).has_differences
    assert compare(tmp_path, BASE, new, raw=True).has_differences


def test_output_only_change(tmp_path):
    new = copy.deepcopy(BASE)
    new["cells"][1]["outputs"][0]["text"] = ["30\n"]
    assert not compare(tmp_path, BASE, new).has_differences
    result = compare(tmp_path, BASE, new, include_output=True)
    assert result.summary.modified == 1
    assert result.changes[0].new_text == "[output] 30"


def test_string_source_is_supported(tmp_path):
    notebook = copy.deepcopy(BASE)
    notebook["cells"][1]["source"] = "x = 1\ny = 2\nprint(x + y)"
    assert not compare(tmp_path, BASE, notebook).has_differences


@pytest.mark.parametrize("content", ["{not json", "[]", '{"cells": 3}', '{"cells": [1]}'])
def test_invalid_notebook(tmp_path, content):
    path = tmp_path / "bad.ipynb"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(InvalidNotebookError):
        load_document(str(path))


def test_raw_mode_reads_json_text(tmp_path):
    doc = load_document(write(tmp_path, "n.ipynb", BASE), ParseOptions(raw=True))
    assert doc.kind == "text" and doc.lines[0].startswith("{")


def test_non_text_outputs_are_summarised(tmp_path):
    notebook = copy.deepcopy(BASE)
    notebook["cells"][1]["outputs"] = [
        {"output_type": "display_data", "data": {"image/png": "iVBOR..."}},
        {"output_type": "error", "ename": "ValueError", "evalue": "bad"},
    ]
    doc = load_document(write(tmp_path, "n.ipynb", notebook), ParseOptions(include_output=True))
    assert doc.lines[-2:] == ["[output] <image/png>", "[output] ValueError: bad"]
