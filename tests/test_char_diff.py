"""Tests for the character-level diff (same Myers engine, characters)."""

import random

import pytest

from differentiater.core import char_diff
from differentiater.core.char_diff import (
    diff_characters,
    diff_characters_bounded,
    new_side,
    old_side,
    similarity_ratio,
)
from differentiater.core.patch import apply_character_operations
from differentiater.models.diff_result import CharacterOperation, OperationType

E, I, D = OperationType.EQUAL, OperationType.INSERT, OperationType.DELETE


def runs(old, new):
    ops = diff_characters(old, new)
    assert apply_character_operations(old, ops) == new
    assert old_side(ops) == old and new_side(ops) == new
    return [(op.operation, op.text) for op in ops]


def changed(old, new, kind):
    return "".join(text for op, text in runs(old, new) if op == kind)


def test_identical_strings():
    assert runs("same", "same") == [(E, "same")]


def test_empty_strings():
    assert runs("", "") == []
    assert runs("", "abc") == [(I, "abc")]
    assert runs("abc", "") == [(D, "abc")]


def test_single_character_insertion():
    assert runs("cat", "cart") == [(E, "ca"), (I, "r"), (E, "t")]


def test_single_character_deletion():
    assert runs("cart", "cat") == [(E, "ca"), (D, "r"), (E, "t")]


def test_single_character_replacement():
    assert runs("x = 10", "x = 20") == [(E, "x = "), (D, "1"), (I, "2"), (E, "0")]


def test_prefix_change():
    assert runs("hello", "Jello") == [(D, "h"), (I, "J"), (E, "ello")]


def test_suffix_change():
    assert runs("return a + b", "return a + b + c") == [(E, "return a + b"), (I, " + c")]


def test_middle_change():
    assert changed('print("Hello")', 'print("Hello World")', I) == " World"


def test_multiple_changes():
    assert changed("def calculate(a, b):", "def calculate(a, b, c):", I) == ", c"
    ops = runs("a-b-c", "a+b+c")
    assert [t for op, t in ops if op == D] == ["-", "-"]
    assert [t for op, t in ops if op == I] == ["+", "+"]


def test_completely_different_strings():
    ops = runs("abc", "xyz")
    assert all(op != E for op, _ in ops)


def test_unicode_hindi():
    assert runs("नमस्ते", "नमस्ते दुनिया") == [(E, "नमस्ते"), (I, " दुनिया")]


def test_emoji():
    assert runs("I like 🍎", "I like 🍌🍎") == [(E, "I like "), (I, "🍌"), (E, "🍎")]


def test_tabs_and_trailing_whitespace():
    assert runs("\tx", "\tx  ") == [(E, "\tx"), (I, "  ")]


def test_similarity_ratio():
    assert similarity_ratio(diff_characters("abcd", "abcd")) == 1.0
    assert similarity_ratio(diff_characters("ab", "cd")) == 0.0
    assert similarity_ratio([]) == 1.0


def test_bounded_falls_back_to_whole_line_replacement():
    ops = diff_characters_bounded("a" * 50, "b" * 50, max_edits=10)
    assert ops == [CharacterOperation(D, "a" * 50), CharacterOperation(I, "b" * 50)]


def test_character_diff_uses_the_shared_myers_engine(monkeypatch):
    calls = []
    original = char_diff.myers_diff

    def spy(a, b, **kwargs):
        calls.append((a, b))
        return original(a, b, **kwargs)

    monkeypatch.setattr(char_diff, "myers_diff", spy)
    diff_characters("abc", "abd")
    assert calls == [(list("abc"), list("abd"))]


@pytest.mark.parametrize("seed", range(5))
def test_randomized_character_reconstruction(seed):
    rng = random.Random(seed)
    alphabet = "ab c\tनम🍎"
    for _ in range(300):
        old = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 20)))
        new = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 20)))
        assert apply_character_operations(old, diff_characters(old, new)) == new
