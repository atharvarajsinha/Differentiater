"""Tests for the generic Myers engine."""

import random

import pytest

from differentiater.core.myers import (
    DELETE,
    EQUAL,
    INSERT,
    EditLimitExceeded,
    edit_distance,
    myers_diff,
)
from differentiater.core.patch import apply_operations


def lcs_length(a, b):
    """Reference O(NM) LCS used to verify that Myers is optimal."""
    previous = [0] * (len(b) + 1)
    for x in a:
        current = [0]
        for j, y in enumerate(b):
            current.append(previous[j] + 1 if x == y else max(previous[j + 1], current[j]))
        previous = current
    return previous[-1]


def assert_valid_and_shortest(a, b):
    script = myers_diff(a, b)
    assert apply_operations(a, script) == list(b)
    assert edit_distance(script) == len(a) + len(b) - 2 * lcs_length(a, b)
    return script


def test_empty_to_empty():
    assert myers_diff([], []) == []


def test_empty_to_content():
    assert myers_diff([], ["a", "b"]) == [(INSERT, "a"), (INSERT, "b")]


def test_content_to_empty():
    assert myers_diff(["a", "b"], []) == [(DELETE, "a"), (DELETE, "b")]


def test_identical_sequences():
    seq = ["x", "y", "z"]
    assert myers_diff(seq, seq) == [(EQUAL, "x"), (EQUAL, "y"), (EQUAL, "z")]


def test_one_insertion():
    assert myers_diff(["a", "c"], ["a", "b", "c"]) == [
        (EQUAL, "a"), (INSERT, "b"), (EQUAL, "c"),
    ]


def test_one_deletion():
    assert myers_diff(["a", "b", "c"], ["a", "c"]) == [
        (EQUAL, "a"), (DELETE, "b"), (EQUAL, "c"),
    ]


def test_one_replacement_deletes_before_inserts():
    assert myers_diff(["a", "b", "c"], ["a", "X", "c"]) == [
        (EQUAL, "a"), (DELETE, "b"), (INSERT, "X"), (EQUAL, "c"),
    ]


def test_multiple_insertions():
    script = assert_valid_and_shortest(list("ace"), list("abcde"))
    assert [op for op, _ in script].count(INSERT) == 2


def test_multiple_deletions():
    script = assert_valid_and_shortest(list("abcde"), list("ace"))
    assert [op for op, _ in script].count(DELETE) == 2


def test_multiple_replacements():
    script = assert_valid_and_shortest(list("a1b2c3"), list("aXbYcZ"))
    assert edit_distance(script) == 6


def test_paper_example_has_distance_five():
    # The worked example from Myers' paper: ABCABBA -> CBABAC, D = 5.
    script = assert_valid_and_shortest("ABCABBA", "CBABAC")
    assert edit_distance(script) == 5


def test_repeated_values():
    assert_valid_and_shortest(list("aaaa"), list("aaaaaa"))
    assert_valid_and_shortest(list("abababab"), list("babababa"))


def test_duplicate_lines():
    a = ["}", "}", "return x", "}", "}"]
    b = ["}", "return x", "}", "}", "}", "}"]
    assert_valid_and_shortest(a, b)


def test_works_on_strings_and_tuples():
    assert_valid_and_shortest("kitten", "sitting")
    assert_valid_and_shortest((1, 2, 3, 4), (2, 3, 5, 4))


def test_completely_different():
    script = assert_valid_and_shortest(list("abc"), list("xyz"))
    assert edit_distance(script) == 6


def test_large_sequences():
    rng = random.Random(7)
    a = [f"line {i}" for i in range(5000)]
    b = list(a)
    for _ in range(50):
        b[rng.randrange(len(b))] = f"changed {rng.random()}"
    for _ in range(20):
        b.insert(rng.randrange(len(b)), "inserted")
    for _ in range(20):
        del b[rng.randrange(len(b))]
    script = myers_diff(a, b)
    assert apply_operations(a, script) == b
    assert edit_distance(script) <= 2 * 50 + 20 + 20


def test_unrelated_large_sequences_are_cheap_and_exact():
    a = [f"old {i}" for i in range(20000)]
    b = [f"new {i}" for i in range(20000)]
    script = myers_diff(a, b)
    assert edit_distance(script) == 40000
    assert apply_operations(a, script) == b


def test_items_unique_to_one_side_are_spliced_back_in_order():
    a = ["u1", "x", "u2", "y", "u3"]
    b = ["v1", "y", "v2", "x", "v3"]
    assert_valid_and_shortest(a, b)


def test_unhashable_items_still_work():
    a = [[1], [2], [3]]
    b = [[1], [3], [4]]
    script = assert_valid_and_shortest(a, b)
    assert edit_distance(script) == 2


def test_max_edits_limit():
    with pytest.raises(EditLimitExceeded):
        myers_diff(list("abcdef"), list("uvwxyz"), max_edits=3)
    # A limit that is large enough does not change the result.
    assert myers_diff("abc", "abd", max_edits=2) == myers_diff("abc", "abd")


@pytest.mark.parametrize("seed", range(10))
def test_randomized_shortest_and_reconstructs(seed):
    rng = random.Random(seed)
    for _ in range(300):
        a = [rng.choice("abcd") for _ in range(rng.randint(0, 15))]
        b = [rng.choice("abcd") for _ in range(rng.randint(0, 15))]
        assert_valid_and_shortest(a, b)
