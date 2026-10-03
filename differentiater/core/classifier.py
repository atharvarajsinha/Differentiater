"""Turn raw Myers line operations into INSERT / DELETE / MODIFY / EQUAL.

Myers only knows "equal", "delete" and "insert".  A changed line therefore
shows up as a deletion followed by an insertion.  This module decides which
deletions and insertions are really *modifications* of one another.

Strategy
--------
1. **Hunks.**  The Myers script is split into *change hunks*: maximal runs of
   delete/insert operations bounded by equal lines (or the start/end of the
   file).  Only a deletion and an insertion that sit in the same hunk -- i.e.
   that replace each other at the same position between the same unchanged
   anchors -- can be a modification.  A pure insertion block (no deletions
   in its hunk) stays an INSERTION, and vice versa.
2. **Order-preserving alignment.**  Inside a hunk with ``p`` deletions and
   ``q`` insertions, a small dynamic programme picks the order-preserving
   set of (deletion, insertion) pairs with the highest total similarity.  It
   never pairs line 3 of the hunk with line 1 if that would cross another
   pair, so the output stays in file order.
3. **Confirmation with Myers.**  Every candidate pair is confirmed with a
   character-level Myers diff: the pair is a modification only if
   ``2 * matched_chars / (len(old) + len(new)) >= SIMILARITY_THRESHOLD``.
   The character diff computed here is kept and attached to the MODIFY
   operation, so it is never computed twice.

Unpaired lines in a hunk remain DELETE / INSERT operations.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Sequence, Tuple

from differentiater.core.char_diff import (
    DEFAULT_MAX_CHAR_EDITS,
    diff_characters,
    similarity_ratio,
    whole_line_replacement,
)
from differentiater.core.myers import EditLimitExceeded
from differentiater.models.diff_result import (
    CharacterOperation,
    DiffOperation,
    OperationType,
)

#: Minimum character similarity for a delete/insert pair to be a modification.
SIMILARITY_THRESHOLD = 0.4

#: Hunks with more (deletions x insertions) cells than this skip the
#: alignment DP and pair lines positionally (still similarity-checked).
MAX_ALIGNMENT_CELLS = 10_000

Pair = Tuple[int, int]


def classify(operations: Sequence[DiffOperation]) -> List[DiffOperation]:
    """Group related delete/insert operations into modifications."""
    result: List[DiffOperation] = []
    index = 0
    while index < len(operations):
        if operations[index].operation == OperationType.EQUAL:
            result.append(operations[index])
            index += 1
            continue
        end = index
        while end < len(operations) and operations[end].operation != OperationType.EQUAL:
            end += 1
        result.extend(classify_hunk(operations[index:end]))
        index = end
    return result


def classify_hunk(hunk: Sequence[DiffOperation]) -> List[DiffOperation]:
    """Classify one run of consecutive delete/insert operations."""
    deletions = [op for op in hunk if op.operation == OperationType.DELETE]
    insertions = [op for op in hunk if op.operation == OperationType.INSERT]
    if not deletions or not insertions:
        return list(hunk)

    old_texts = [op.old_text or "" for op in deletions]
    new_texts = [op.new_text or "" for op in insertions]
    candidates = _candidate_pairs(old_texts, new_texts)

    confirmed: List[Tuple[int, int, List[CharacterOperation]]] = []
    for d, i in candidates:
        char_ops = confirm_modification(old_texts[d], new_texts[i])
        if char_ops is not None:
            confirmed.append((d, i, char_ops))

    return _merge(deletions, insertions, confirmed)


def confirm_modification(
    old: str, new: str, threshold: float = SIMILARITY_THRESHOLD
) -> Optional[List[CharacterOperation]]:
    """Return the character diff if ``old`` -> ``new`` is a modification.

    Uses a bounded Myers character diff: if the edit distance alone already
    proves the similarity is below ``threshold`` the search stops early.
    """
    total = len(old) + len(new)
    if total == 0:
        return []
    if _multiset_similarity(old, new) < threshold:
        return None  # cheap upper bound already rules it out

    threshold_edits = int((1.0 - threshold) * total)
    max_edits = min(threshold_edits, DEFAULT_MAX_CHAR_EDITS)
    try:
        char_ops = diff_characters(old, new, max_edits=max_edits)
    except EditLimitExceeded:
        if max_edits < threshold_edits:
            # Very long line: too expensive to diff exactly, but the
            # character-multiset check says they are related.
            return whole_line_replacement(old, new)
        return None
    return char_ops if similarity_ratio(char_ops) >= threshold else None


def _candidate_pairs(old_texts: List[str], new_texts: List[str]) -> List[Pair]:
    """Order-preserving (deletion, insertion) pairs worth confirming."""
    p, q = len(old_texts), len(new_texts)
    if p * q > MAX_ALIGNMENT_CELLS:
        return [(k, k) for k in range(min(p, q))]
    return _align(old_texts, new_texts)


def _align(old_texts: List[str], new_texts: List[str]) -> List[Pair]:
    """LCS-style DP maximising total bigram similarity of matched pairs."""
    p, q = len(old_texts), len(new_texts)
    old_profiles = [_Profile(text) for text in old_texts]
    new_profiles = [_Profile(text) for text in new_texts]

    scores: Dict[Pair, float] = {}
    for d in range(p):
        for i in range(q):
            if old_profiles[d].upper_bound(new_profiles[i]) >= SIMILARITY_THRESHOLD:
                scores[(d, i)] = old_profiles[d].bigram_similarity(new_profiles[i])

    # best[d][i]: best total score aligning old[:d] with new[:i]
    best = [[0.0] * (q + 1) for _ in range(p + 1)]
    for d in range(1, p + 1):
        for i in range(1, q + 1):
            value = max(best[d - 1][i], best[d][i - 1])
            score = scores.get((d - 1, i - 1))
            if score is not None:
                value = max(value, best[d - 1][i - 1] + score + 1e-9)
            best[d][i] = value

    pairs: List[Pair] = []
    d, i = p, q
    while d > 0 and i > 0:
        score = scores.get((d - 1, i - 1))
        if score is not None and best[d][i] == best[d - 1][i - 1] + score + 1e-9:
            pairs.append((d - 1, i - 1))
            d -= 1
            i -= 1
        elif best[d][i] == best[d - 1][i]:
            d -= 1
        else:
            i -= 1
    pairs.reverse()
    return pairs


def _merge(
    deletions: List[DiffOperation],
    insertions: List[DiffOperation],
    pairs: List[Tuple[int, int, List[CharacterOperation]]],
) -> List[DiffOperation]:
    """Emit operations so both old and new line numbers stay ascending."""
    result: List[DiffOperation] = []
    d = i = 0
    for pair_d, pair_i, char_ops in pairs:
        result.extend(deletions[d:pair_d])
        result.extend(insertions[i:pair_i])
        old, new = deletions[pair_d], insertions[pair_i]
        result.append(
            DiffOperation(
                operation=OperationType.MODIFY,
                old_line_number=old.old_line_number,
                new_line_number=new.new_line_number,
                old_text=old.old_text,
                new_text=new.new_text,
                char_operations=char_ops,
            )
        )
        d, i = pair_d + 1, pair_i + 1
    result.extend(deletions[d:])
    result.extend(insertions[i:])
    return result


def _multiset_similarity(old: str, new: str) -> float:
    """Upper bound of the Myers similarity using character counts only."""
    shared = sum((Counter(old) & Counter(new)).values())
    return 2.0 * shared / (len(old) + len(new))


class _Profile:
    """Pre-computed character statistics of one line for fast scoring."""

    __slots__ = ("length", "chars", "bigrams", "bigram_count")

    def __init__(self, text: str) -> None:
        self.length = len(text)
        self.chars = Counter(text)
        self.bigrams = Counter(text[k:k + 2] for k in range(len(text) - 1))
        self.bigram_count = max(len(text) - 1, 0)

    def upper_bound(self, other: "_Profile") -> float:
        total = self.length + other.length
        if total == 0:
            return 1.0
        return 2.0 * sum((self.chars & other.chars).values()) / total

    def bigram_similarity(self, other: "_Profile") -> float:
        total = self.bigram_count + other.bigram_count
        if total == 0:
            return self.upper_bound(other)
        return 2.0 * sum((self.bigrams & other.bigrams).values()) / total
