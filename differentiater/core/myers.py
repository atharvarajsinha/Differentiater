"""Generic implementation of Eugene W. Myers' O(ND) difference algorithm.

Reference: E. W. Myers, "An O(ND) Difference Algorithm and Its Variations",
Algorithmica 1 (1986), pp. 251-266.

This module is the single diff engine of Differentiater.  It knows nothing
about files, lines, characters or terminals: it compares two *sequences* of
hashable/comparable items and returns the shortest edit script that turns the
first sequence into the second.  The line-level diff feeds it lists of lines
and the character-level diff feeds it lists of characters.

Key ideas
---------
Edit graph
    For sequences ``a`` (length N) and ``b`` (length M) imagine an
    (N+1) x (M+1) grid.  Point ``(x, y)`` means "the first ``x`` items of
    ``a`` have been consumed and the first ``y`` items of ``b`` have been
    produced".  From each point there are up to three moves:

    * right  ``(x, y) -> (x+1, y)``   delete ``a[x]``          (cost 1)
    * down   ``(x, y) -> (x, y+1)``   insert ``b[y]``          (cost 1)
    * diagonal ``(x, y) -> (x+1, y+1)`` keep ``a[x]`` when ``a[x] == b[y]`` (cost 0)

    Any path from ``(0, 0)`` to ``(N, M)`` is an edit script; the cheapest
    path is the *shortest edit script* (SES).

Diagonals ``k``
    Every point lies on diagonal ``k = x - y``.  A right move goes to
    ``k + 1``, a down move to ``k - 1``, a diagonal move stays on ``k``.
    After exactly ``D`` edits the path must end on a diagonal in
    ``{-D, -D + 2, ..., D - 2, D}``.

The ``V`` array
    ``V[k]`` stores the furthest ``x`` reached on diagonal ``k`` using the
    current number of edits ``D``.  Knowing ``x`` and ``k`` is enough to
    recover ``y = x - k``, so a single integer per diagonal describes the
    whole frontier.

Snakes
    A *snake* is one edit (right or down) followed by as many free diagonal
    moves as possible.  Greedily following diagonals is always safe because
    matching items never makes a path longer.

Search
    For ``D = 0, 1, 2, ...`` and every diagonal ``k`` reachable with ``D``
    edits, extend from the better of the two neighbouring diagonals
    (``k + 1`` via a down move or ``k - 1`` via a right move), follow the
    snake, and record the furthest-reaching ``x`` in ``V[k]``.  The first
    ``D`` at which ``(N, M)`` is reached is the length of the SES.

Backtracking
    A snapshot of ``V`` is kept for every ``D``.  Starting at ``(N, M)`` we
    walk the snapshots backwards, asking at each step "which neighbouring
    diagonal did this path come from?" -- exactly the same decision the
    forward pass made.  That yields, in reverse, the snake (equal items) and
    the single insert/delete that preceded it.

Complexity
    Time  ``O((N + M) * D)`` worst case, ``O(N + M + D^2)`` expected.
    Space ``O(N + M)`` for the working ``V`` array plus ``O(D^2)`` for the
    per-step snapshots needed for backtracking.  Common prefixes and suffixes
    are trimmed before the search, which keeps ``N`` and ``M`` small for the
    typical "few local changes in a big file" case.

Preprocessing (exactness preserved)
    1. A common prefix and suffix are trimmed first.
    2. Items that occur in only one of the two sequences can never be part of
       a longest common subsequence, so they are certainly deletions or
       insertions.  They are set aside before the search and spliced back in
       afterwards (the same trick GNU diff uses).  For two unrelated files
       this shrinks the search to almost nothing.
    Neither step changes the length of the result: it is still a shortest
    edit script.
"""

from __future__ import annotations

from array import array
from typing import List, Optional, Sequence, Tuple, TypeVar

EQUAL = "equal"
INSERT = "insert"
DELETE = "delete"

T = TypeVar("T")

#: One step of an edit script: ``(operation, item)``.
EditOperation = Tuple[str, T]


class EditLimitExceeded(Exception):
    """Raised when the shortest edit script would exceed ``max_edits``.

    Callers use this as a safety valve for pathological inputs (for example
    two unrelated 10,000-character lines) where an exact diff is not worth
    the cost.
    """

    def __init__(self, limit: int) -> None:
        super().__init__(f"shortest edit script exceeds {limit} edits")
        self.limit = limit


def myers_diff(
    a: Sequence[T],
    b: Sequence[T],
    *,
    max_edits: Optional[int] = None,
) -> List[EditOperation]:
    """Return the shortest edit script that transforms ``a`` into ``b``.

    Args:
        a: The original sequence (e.g. lines of file A, characters of a line).
        b: The target sequence.
        max_edits: Optional upper bound on the number of insertions plus
            deletions.  If the shortest script is longer,
            :class:`EditLimitExceeded` is raised.

    Returns:
        A list of ``(operation, item)`` tuples where ``operation`` is one of
        ``"equal"``, ``"delete"`` or ``"insert"``.  ``equal`` and ``delete``
        carry the item from ``a``; ``insert`` carries the item from ``b``.
        Applying the operations in order to ``a`` reproduces ``b`` exactly.
    """
    n, m = len(a), len(b)

    # Trimming a common prefix/suffix never changes the length of the
    # shortest edit script, and it removes most of the work for files that
    # differ in only a few places.
    prefix = _common_prefix_length(a, b)
    suffix = _common_suffix_length(a, b, prefix)

    script: List[EditOperation] = [(EQUAL, a[i]) for i in range(prefix)]
    script.extend(
        _diff_middle(a[prefix:n - suffix], b[prefix:m - suffix], max_edits)
    )
    script.extend((EQUAL, a[i]) for i in range(n - suffix, n))
    return script


def edit_distance(script: Sequence[EditOperation]) -> int:
    """Return ``D``: the number of insertions plus deletions in ``script``."""
    return sum(1 for operation, _ in script if operation != EQUAL)


def _common_prefix_length(a: Sequence[T], b: Sequence[T]) -> int:
    limit = min(len(a), len(b))
    i = 0
    while i < limit and a[i] == b[i]:
        i += 1
    return i


def _common_suffix_length(a: Sequence[T], b: Sequence[T], prefix: int) -> int:
    """Length of the common suffix that does not overlap the prefix."""
    limit = min(len(a), len(b)) - prefix
    i = 0
    while i < limit and a[len(a) - 1 - i] == b[len(b) - 1 - i]:
        i += 1
    return i


def _diff_middle(
    a: Sequence[T], b: Sequence[T], max_edits: Optional[int]
) -> List[EditOperation]:
    """Diff the part of the sequences left after prefix/suffix trimming."""
    if not a or not b:
        # One side is empty: the only possible script is all deletes or all
        # inserts, no search required.
        if max_edits is not None and len(a) + len(b) > max_edits:
            raise EditLimitExceeded(max_edits)
        return [(DELETE, item) for item in a] + [(INSERT, item) for item in b]

    shared = _positions_of_shared_items(a, b)
    discarded = 0 if shared is None else len(a) + len(b) - len(shared[0]) - len(shared[1])
    if shared is None or discarded == 0:
        return _backtrack(a, b, _shortest_edit_trace(a, b, max_edits))

    # Items unique to one side are certain edits; search only the rest.
    if max_edits is not None:
        if discarded > max_edits:
            raise EditLimitExceeded(max_edits)
        max_edits -= discarded
    kept_a, kept_b = shared
    core = _diff_middle([a[i] for i in kept_a], [b[j] for j in kept_b], max_edits)
    return _restore_discarded(a, b, kept_a, kept_b, core)


def _positions_of_shared_items(
    a: Sequence[T], b: Sequence[T]
) -> Optional[Tuple[List[int], List[int]]]:
    """Indices of the items of ``a`` that occur in ``b`` and vice versa.

    Returns ``None`` for unhashable items (the optimisation is then skipped).
    """
    try:
        items_a, items_b = set(a), set(b)
    except TypeError:
        return None
    kept_a = [i for i, item in enumerate(a) if item in items_b]
    kept_b = [j for j, item in enumerate(b) if item in items_a]
    return kept_a, kept_b


def _restore_discarded(
    a: Sequence[T],
    b: Sequence[T],
    kept_a: List[int],
    kept_b: List[int],
    core: List[EditOperation],
) -> List[EditOperation]:
    """Splice the set-aside unique items back into the filtered script.

    Every original item between two kept items is emitted as a deletion (from
    ``a``) or insertion (from ``b``) right before the next kept item that the
    filtered script consumes, so the script stays in sequence order.
    """
    script: List[EditOperation] = []
    x = y = 0     # next unconsumed position in a / b
    fa = fb = 0   # next unconsumed position in kept_a / kept_b
    for operation, _ in core:
        if operation != INSERT:
            target = kept_a[fa]
            script.extend((DELETE, a[i]) for i in range(x, target))
            x, fa = target, fa + 1
        if operation != DELETE:
            target = kept_b[fb]
            script.extend((INSERT, b[j]) for j in range(y, target))
            y, fb = target, fb + 1
        if operation == EQUAL:
            script.append((EQUAL, a[x]))
        elif operation == DELETE:
            script.append((DELETE, a[x]))
        else:
            script.append((INSERT, b[y]))
        if operation != INSERT:
            x += 1
        if operation != DELETE:
            y += 1
    script.extend((DELETE, a[i]) for i in range(x, len(a)))
    script.extend((INSERT, b[j]) for j in range(y, len(b)))
    return script


def _shortest_edit_trace(
    a: Sequence[T], b: Sequence[T], max_edits: Optional[int]
) -> List["array[int]"]:
    """Run the greedy forward search and return the ``V`` snapshots.

    ``trace[d]`` holds the furthest-reaching ``x`` for diagonals
    ``k = -d, -d+1, ..., d`` after ``d`` edits, stored at index ``k + d``.
    The last snapshot is the one in which ``(len(a), len(b))`` was reached,
    so ``len(trace) - 1`` is the edit distance ``D``.  Snapshots are compact
    machine-integer arrays: they are the O(D^2) part of the memory cost.
    """
    n, m = len(a), len(b)
    limit = n + m if max_edits is None else min(n + m, max_edits)

    # V is indexed by diagonal k in [-limit-1, limit+1]; ``offset`` maps k to
    # a non-negative list index.  V[1] = 0 seeds the d = 0 step so that it
    # behaves like a "down move" from the virtual point (0, -1).
    offset = limit + 1
    v = [0] * (2 * limit + 3)
    trace: List["array[int]"] = []

    for d in range(limit + 1):
        for k in range(-d, d + 1, 2):
            index = offset + k
            # Choose the neighbouring diagonal to extend from:
            #   * k == -d: only reachable by a down move from k + 1.
            #   * k ==  d: only reachable by a right move from k - 1.
            #   * otherwise take whichever neighbour reached further in x.
            # Ties go to the down move, which makes deletions come before
            # insertions in a replaced block (the conventional diff order).
            if k == -d or (k != d and v[index - 1] < v[index + 1]):
                x = v[index + 1]          # down move: insertion, x unchanged
            else:
                x = v[index - 1] + 1      # right move: deletion, x advances
            y = x - k

            # Follow the snake: free diagonal moves while items match.
            while x < n and y < m and a[x] == b[y]:
                x += 1
                y += 1

            v[index] = x

            if x >= n and y >= m:
                # Reached the bottom-right corner with d edits: this is the
                # shortest edit script.
                trace.append(array("q", v[offset - d: offset + d + 1]))
                return trace

        trace.append(array("q", v[offset - d: offset + d + 1]))

    # Only reachable when ``max_edits`` cut the search short.
    raise EditLimitExceeded(limit)


def _backtrack(
    a: Sequence[T], b: Sequence[T], trace: List["array[int]"]
) -> List[EditOperation]:
    """Reconstruct the edit script by walking the ``V`` snapshots backwards."""
    x, y = len(a), len(b)
    reversed_script: List[EditOperation] = []

    for d in range(len(trace) - 1, 0, -1):
        previous = trace[d - 1]        # V after d-1 edits, index = k + (d-1)
        k = x - y

        # Repeat the forward pass's decision to learn which diagonal the
        # path arrived from.
        if k == -d or (
            k != d and previous[k - 1 + d - 1] < previous[k + 1 + d - 1]
        ):
            previous_k = k + 1         # arrived by a down move (insert)
        else:
            previous_k = k - 1         # arrived by a right move (delete)

        previous_x = previous[previous_k + d - 1]
        previous_y = previous_x - previous_k

        # Undo the snake: every diagonal step is an equal item.
        while x > previous_x and y > previous_y:
            x -= 1
            y -= 1
            reversed_script.append((EQUAL, a[x]))

        # Undo the single edit that started this snake.
        if previous_k == k + 1:
            y -= 1
            reversed_script.append((INSERT, b[y]))
        else:
            x -= 1
            reversed_script.append((DELETE, a[x]))

    # Whatever is left is the d = 0 snake starting at (0, 0).
    while x > 0 and y > 0:
        x -= 1
        y -= 1
        reversed_script.append((EQUAL, a[x]))

    reversed_script.reverse()
    return reversed_script
