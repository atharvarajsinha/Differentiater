"""Tests for grouping delete/insert pairs into modifications."""

from differentiater.core.classifier import classify, confirm_modification
from differentiater.core.line_diff import diff_lines
from differentiater.models.diff_result import DiffOperation, OperationType

E, I, D, M = (OperationType.EQUAL, OperationType.INSERT,
              OperationType.DELETE, OperationType.MODIFY)


def kinds(old, new):
    return [op.operation for op in diff_lines(old, new)]


def test_replacement_between_anchors_is_modification():
    ops = diff_lines(["hello", "world", "foo"], ["hello", "beautiful world", "foo"])
    assert [op.operation for op in ops] == [E, M, E]
    modify = ops[1]
    assert (modify.old_text, modify.new_text) == ("world", "beautiful world")
    assert (modify.old_line_number, modify.new_line_number) == (2, 2)


def test_pure_insertion_block_stays_insertion():
    assert kinds(["a", "c"], ["a", "b1", "b2", "c"]) == [E, I, I, E]


def test_pure_deletion_block_stays_deletion():
    assert kinds(["a", "b1", "b2", "c"], ["a", "c"]) == [E, D, D, E]


def test_unrelated_replacement_is_not_modification():
    assert kinds(["start", "x = compute()", "end"], ["start", "########", "end"]) == [E, D, I, E]


def test_insert_and_delete_in_different_hunks_are_not_paired():
    old = ["keep", "return a + b", "anchor"]
    new = ["keep", "anchor", "return a + b + c"]
    # The deletion and the insertion are separated by the "anchor" line, so
    # they are a move-like change, not an in-place modification.
    assert kinds(old, new) == [E, D, E, I]


def test_uneven_hunk_pairs_best_matching_lines():
    old = ["head", "alpha = 1", "beta = 2", "tail"]
    new = ["head", "brand new line", "alpha = 10", "beta = 20", "tail"]
    ops = diff_lines(old, new)
    assert [op.operation for op in ops] == [E, I, M, M, E]
    assert ops[2].old_text == "alpha = 1" and ops[2].new_text == "alpha = 10"
    assert ops[3].old_text == "beta = 2" and ops[3].new_text == "beta = 20"


def test_modification_carries_character_diff():
    ops = diff_lines(["return a + b"], ["return a + b + c"])
    assert ops[0].operation == M
    assert [(c.operation, c.text) for c in ops[0].char_operations] == [
        (E, "return a + b"), (I, " + c"),
    ]


def test_line_numbers_stay_monotonic_after_classification():
    old = ["a", "b one", "b two", "c", "d"]
    new = ["a", "x", "b one!", "y", "b two!", "c", "e"]
    ops = diff_lines(old, new)
    old_numbers = [op.old_line_number for op in ops if op.old_line_number]
    new_numbers = [op.new_line_number for op in ops if op.new_line_number]
    assert old_numbers == sorted(old_numbers) == list(range(1, len(old) + 1))
    assert new_numbers == sorted(new_numbers) == list(range(1, len(new) + 1))


def test_classify_leaves_equal_operations_untouched():
    ops = [DiffOperation(E, 1, 1, "same", "same")]
    assert classify(ops) == ops


def test_confirm_modification_threshold():
    assert confirm_modification("username = 'Atharva'", "username = 'Rahul'") is not None
    assert confirm_modification("abc", "xyz") is None
    assert confirm_modification("", "") == []


def test_very_long_related_lines_do_not_explode():
    old = "".join(chr(97 + (i * 7) % 26) for i in range(6000))
    new = "".join(chr(97 + (i * 11) % 26) for i in range(6000))
    ops = diff_lines([old], [new])
    assert len(ops) in (1, 2)  # either a coarse modification or delete+insert
