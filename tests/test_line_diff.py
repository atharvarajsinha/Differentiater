"""Tests for the line-level diff and the reconstruction property."""

import random

import pytest

from differentiater.core import line_diff
from differentiater.core.line_diff import diff_lines
from differentiater.core.patch import apply_operations
from differentiater.engine import compare_documents
from differentiater.models.diff_result import DiffSummary, OperationType
from differentiater.models.document import CompareOptions, LoadedDocument

E, I, D, M = (OperationType.EQUAL, OperationType.INSERT,
              OperationType.DELETE, OperationType.MODIFY)


def summary(old, new, **options):
    ops = diff_lines(old, new, options=CompareOptions(**options))
    return DiffSummary.from_operations(ops, len(old), len(new))


def test_identical_files():
    s = summary(["a", "b"], ["a", "b"])
    assert s.is_identical and s.unchanged == 2


def test_only_insertion():
    ops = diff_lines(["a", "b"], ["a", "new", "b"])
    assert [op.operation for op in ops] == [E, I, E]
    assert ops[1].new_line_number == 2 and ops[1].old_line_number is None


def test_only_deletion():
    ops = diff_lines(["a", "gone", "b"], ["a", "b"])
    assert [op.operation for op in ops] == [E, D, E]
    assert ops[1].old_line_number == 2 and ops[1].new_line_number is None


def test_only_modification():
    ops = diff_lines(["x = 10"], ["x = 20"])
    assert [op.operation for op in ops] == [M]


def test_spec_example_three_modifications():
    old = ["def calculate(a, b):", "    return a + b", "", 'print("Hello")']
    new = ["def calculate(a, b, c):", "    return a + b + c", "", 'print("Hello World")']
    s = summary(old, new)
    assert (s.inserted, s.deleted, s.modified, s.unchanged) == (0, 0, 3, 1)


def test_same_line_count_can_be_all_modifications():
    old = [f"value_{i} = {i}" for i in range(10)]
    new = [f"value_{i} = {i + 100}" for i in range(10)]
    s = summary(old, new)
    assert s.modified == 10 and s.line_delta == 0


def test_mixed_changes():
    old = ["import os", "import sys", "x = 10", "print(x)", "end"]
    new = ["import os", "x = 20", "print(x)", "print('done')", "end"]
    s = summary(old, new)
    assert (s.inserted, s.deleted, s.modified, s.unchanged) == (1, 1, 1, 3)
    assert s.total_changes == 3


def test_multiple_modifications_keep_line_numbers():
    ops = diff_lines(["a1", "keep", "b1"], ["a2", "keep", "b2"])
    mods = [op for op in ops if op.operation == M]
    assert [(m.old_line_number, m.new_line_number) for m in mods] == [(1, 1), (3, 3)]


def test_empty_files():
    assert diff_lines([], []) == []
    assert [op.operation for op in diff_lines([], ["a"])] == [I]
    assert [op.operation for op in diff_lines(["a"], [])] == [D]


def test_ignore_space():
    old, new = ["if x:", "    return  1"], ["if  x :", "\treturn 1"]
    assert not summary(old, new).is_identical
    assert summary(old, new, ignore_space=True).is_identical


def test_ignore_blank_lines():
    old, new = ["a", "", "b"], ["a", "b", "", ""]
    assert not summary(old, new).is_identical
    assert summary(old, new, ignore_blank_lines=True).is_identical


def test_missing_final_newline_is_a_difference():
    ops = diff_lines(["a", "b"], ["a", "b"], old_has_final_newline=False)
    assert [op.operation for op in ops] == [E, M]
    both = diff_lines(["a", "b"], ["a", "b"], old_has_final_newline=False,
                      new_has_final_newline=False)
    assert all(op.operation == E for op in both)


def test_line_diff_uses_the_shared_myers_engine(monkeypatch):
    calls = []
    original = line_diff.myers_diff

    def spy(a, b, **kwargs):
        calls.append(len(a))
        return original(a, b, **kwargs)

    monkeypatch.setattr(line_diff, "myers_diff", spy)
    diff_lines(["a", "b"], ["a", "c"])
    assert calls == [2]


def test_engine_summary_counts_come_from_operations():
    doc_a = LoadedDocument("a", ["one", "x = 2", "three"])
    doc_b = LoadedDocument("b", ["one", "x = 3", "three"])
    result = compare_documents(doc_a, doc_b)
    assert result.summary.modified == 1 and result.has_differences
    unrelated = compare_documents(doc_a, LoadedDocument("b", ["one", "????", "three"]))
    assert (unrelated.summary.deleted, unrelated.summary.inserted) == (1, 1)


# ---------------------------------------------------------------------------
# Critical correctness check: apply_operations(a, diff(a, b)) == b
# ---------------------------------------------------------------------------

RECONSTRUCTION_CASES = [
    ([], []),
    ([], ["a"]),
    (["a"], []),
    (["a", "b", "c"], ["a", "b", "c"]),
    (["a", "b", "c"], ["c", "b", "a"]),
    (["x"] * 5, ["x"] * 3),
    (["}", "}", "}"], ["}", "return", "}", "}"]),
    (["def f(a):", "    return a"], ["def f(a, b):", "    return a + b", ""]),
    (["नमस्ते", "😀"], ["नमस्ते दुनिया", "😀😀"]),
    (["\tindented", "trailing  "], ["    indented", "trailing"]),
]


@pytest.mark.parametrize("old, new", RECONSTRUCTION_CASES)
def test_reconstruction_cases(old, new):
    assert apply_operations(old, diff_lines(old, new)) == new


@pytest.mark.parametrize("seed", range(20))
def test_randomized_reconstruction(seed):
    rng = random.Random(seed)
    vocabulary = ["", "a", "b", "x = 1", "x = 2", "return a + b", "return a + b + c", "}", "😀"]
    for _ in range(200):
        old = [rng.choice(vocabulary) for _ in range(rng.randint(0, 25))]
        new = [rng.choice(vocabulary) for _ in range(rng.randint(0, 25))]
        ops = diff_lines(old, new)
        assert apply_operations(old, ops) == new
        s = DiffSummary.from_operations(ops, len(old), len(new))
        assert s.unchanged + s.deleted + s.modified == len(old)
        assert s.unchanged + s.inserted + s.modified == len(new)
