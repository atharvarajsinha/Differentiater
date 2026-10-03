# Differentiater

**Differentiater** is a command-line tool that compares two files and shows
exactly what changed: which lines were **inserted**, **deleted**, **modified**
or left **unchanged**, and, inside each modified line, which **characters**
changed.

Its core is a from-scratch implementation of **Myers' O(ND) diff
algorithm**. The same engine runs at two levels: once over lines, and again
over the characters of each modified line. It does not use `difflib`,
`SequenceMatcher`, `git diff` or any third-party diff library.

```text
Git:            version control + repository + commits + branches + diff
Differentiater: file comparison + difference detection only
```

Differentiater is not a version-control system. It has no repository, history
or patches. It answers one question: *what exactly changed from file A to
file B?*

---

## Features

- **Myers' shortest-edit-script algorithm**, implemented from scratch and
  shared by the line and character levels
- **Line-level diff (Part A)** with old and new line numbers, context lines and
  collapsed unchanged blocks
- **Character-level diff (Part B)**: changed characters are highlighted in color
  and marked with `^` underneath
- **Modification detection**: related delete/insert pairs become
  `~ MODIFICATION`, and real insertion or deletion blocks stay as they are
- **Summary statistics** computed from the actual diff operations, not from
  line counts
- **JSON output** that other programs can consume
- **Logical Jupyter notebook diffs**: compares cell sources and ignores noisy
  metadata, execution counts and outputs by default
- **Robust text handling**: UTF-8 (with or without BOM), UTF-16/32 with a BOM,
  LF/CRLF/CR, Unicode, Hindi, emoji, tabs, trailing whitespace, missing
  final newline and empty files
- **Binary-file detection** and clean error messages (no tracebacks)
- `--ignore-space` and `--ignore-blank-lines` change only how lines are
  compared. Files are never modified.
- **Exit codes** for scripting: `0` identical, `1` different, `2` error

## Installation

Requires Python 3.9 or newer.

```bash
git clone <this repository> Differentiater
cd Differentiater
pip install -e .            # installs the `differentiater` command
pip install -e ".[dev]"     # ...plus pytest for running the tests
```

Check the installation:

```bash
differentiater --version
```

You can also run it as a module: `python -m differentiater old.py new.py`.

The only runtime dependency is [`rich`](https://github.com/Textualize/rich),
which is used for terminal colors. The diff algorithm uses only the Python
standard library.

## Quick Start

```bash
differentiater examples/old.py examples/new.py
```

```text
════════════════════════════════════════════════════════════
                       DIFFERENTIATER
════════════════════════════════════════════════════════════

FILE A       : examples/old.py
FILE B       : examples/new.py

────────────────────────────────────────────────────────────
SUMMARY
────────────────────────────────────────────────────────────

Old Lines    : 16
New Lines    : 18
Line Delta   : +2

Inserted     : 2
Deleted      : 0
Modified     : 6
Unchanged    : 10

Chars Added  : 25
Chars Removed: 10

Total Changes: 8
════════════════════════════════════════════════════════════

────────────────────────────────────────────────────────────
PART A — LINE DIFF
────────────────────────────────────────────────────────────

   1  1 | import os
   2  2 | import sys

+ INSERTION

+     3 | import json

   3  4 |
   4  5 |

~ MODIFICATION

-  5    | def calculate(a, b):
+     6 | def calculate(a, b, c):
...

────────────────────────────────────────────────────────────
PART B — CHARACTER DIFF
────────────────────────────────────────────────────────────

~ MODIFICATION

-  5    | def calculate(a, b):
+     6 | def calculate(a, b, c):
                         ^^^

~ MODIFICATION

- 14    | username = "Atharva"
                      ^^^ ^^^
+    15 | username = "Rahul"
                      ^ ^^^
...
```

The two number columns are the **old** and **new** line numbers. A blank
column means the line does not exist on that side: deleted lines have only an
old number and inserted lines have only a new one.

In a color terminal, deletions are red, insertions green, modification labels
yellow and line numbers dim. Changed characters inside a modified line get a
solid background highlight.

## CLI Usage

```text
differentiater <file_a> <file_b> [options]

Options:
  --part {A,B}          show only Part A (line diff) or Part B (character diff)
  --summary             show the summary
  --json                print machine-readable JSON
  --context N           unchanged context lines around changes (default 3)
  --ignore-space        ignore all whitespace differences when comparing lines
  --ignore-blank-lines  ignore blank lines when comparing
  --raw                 compare notebooks as raw JSON text
  --include-output      include code-cell outputs when comparing notebooks
  --no-color            disable colored output (no ANSI escape codes at all)
  --version             show the version and exit
  -h, --help            show help and exit
```

| Command                                   | Shows                         |
|-------------------------------------------|-------------------------------|
| `differentiater a b`                      | Summary + Part A + Part B     |
| `differentiater a b --part A`             | Part A only                   |
| `differentiater a b --part B`             | Part B only                   |
| `differentiater a b --summary`            | Summary only                  |
| `differentiater a b --summary --part A`   | Summary + Part A              |
| `differentiater a b --json`               | JSON document                 |

Color is turned off automatically when output is not a terminal, and when the
`NO_COLOR` environment variable is set.

### Part A: line diff

Part A shows every change with `--context` unchanged lines around it. Changes
are grouped under labels:

```text
+ INSERTION      lines that exist only in file B
- DELETION       lines that exist only in file A
~ MODIFICATION   a line of A that was edited into a line of B
```

Long runs of unchanged lines are collapsed:

```text
  10 10 | def calculate():
          │
          │ 20 unchanged lines
          │
  31 31 | def main():

~ MODIFICATION

- 32    |     return x
+    32 |     return x + 1
```

`--context 0` shows only changed lines. `--context 5` shows five lines on each
side of every change.

### Part B: character diff

Part B lists every change again. For each modification it runs Myers a second
time, over the characters of the old and new line, and highlights the
characters that were actually inserted or deleted:

```text
~ MODIFICATION

- 1   | username = "Atharva"
                    ^^^ ^^^
+   1 | username = "Rahul"
                    ^ ^^^
```

`^` under the `-` line marks deleted characters, and `^` under the `+` line
marks inserted characters. The markers are always printed, so the diff is
readable even with `--no-color`. They account for double-width characters such
as emoji and CJK.

The character diff only runs on lines classified as modifications, never on
unchanged lines.

## Myers Algorithm

The engine is in [`differentiater/core/myers.py`](differentiater/core/myers.py).
It is generic: `myers_diff(a, b)` takes any two sequences of comparable items
and returns a list of `("equal" | "delete" | "insert", item)` tuples.

```python
myers_diff(lines_a, lines_b)                  # line level
myers_diff(list(old_line), list(new_line))    # character level
```

### What is Myers diff?

Eugene W. Myers published *An O(ND) Difference Algorithm and Its Variations*
in 1986. It finds the **shortest edit script** (SES): the smallest number of
single-item insertions and deletions that turn sequence A into sequence B.
Equivalently, it finds a **longest common subsequence** (LCS). Git, GNU diff
and most modern diff tools use it or a variant of it.

### Why use Myers?

- **Optimal**: the result always has the fewest possible edits.
- **Fast when files are similar**: the running time depends on `D`, the
  number of differences, not only on the file sizes. Comparing two
  100,000-line files that differ in a handful of places takes milliseconds.
- **Readable output**: its greedy preference for long runs of matching lines
  produces diffs that people find natural.

The textbook dynamic-programming LCS needs `O(N·M)` time and memory, which is
10¹⁰ cells for two 100k-line files. Myers avoids that.

### What is an edit graph?

Lay sequence A along the x-axis and sequence B along the y-axis. Point
`(x, y)` means "the first `x` items of A have been consumed and the first `y`
items of B have been produced". From each point you can move:

| Move                       | Meaning        | Cost |
|----------------------------|----------------|------|
| right `(x+1, y)`           | delete `A[x]`  | 1    |
| down `(x, y+1)`            | insert `B[y]`  | 1    |
| diagonal `(x+1, y+1)`      | keep `A[x]`. Only allowed when `A[x] == B[y]` | 0    |

Every path from `(0, 0)` to `(N, M)` is a valid edit script. The cheapest path
is the shortest edit script. Free diagonal moves exist only where the two
sequences have the same item, so the cheapest path uses as many of them as
possible.

### What are diagonals?

Every point lies on a **diagonal** `k = x − y`. A right move goes from `k` to
`k+1`, a down move from `k` to `k−1`, and a diagonal move stays on `k`. After
exactly `D` edits a path can only end on one of the diagonals
`−D, −D+2, …, D−2, D`.

### What is the V array?

`V[k]` stores the **furthest x-coordinate** reached on diagonal `k` with the
current number of edits. Since `y = x − k`, one integer per diagonal describes
the whole search frontier. To find the best point on diagonal `k` after `D`
edits, Myers looks at its two neighbours from step `D−1`:

- arrive from `k+1` with a **down** move (insertion): `x = V[k+1]`
- arrive from `k−1` with a **right** move (deletion): `x = V[k−1] + 1`

It takes whichever neighbour reached further, which is why the result is called
the *furthest-reaching path*.

### What is a snake?

A **snake** is one edit followed by as many free diagonal moves as possible,
for as long as `A[x] == B[y]`. Following diagonals greedily is always safe,
because matching items never makes the edit script longer.

### How does the search work?

```text
for D = 0, 1, 2, ...:
    for k = -D, -D+2, ..., D:
        pick the better neighbour (k-1 or k+1)
        take one edit, then follow the snake
        V[k] = furthest x reached
        if (x, y) == (N, M): the shortest edit script has D edits, stop
    remember a snapshot of V for this D
```

### How does backtracking work?

The forward pass only finds `D`, the length of the script. To recover the
edits themselves, Differentiater keeps a snapshot of `V` for each `D`. Starting
at `(N, M)`, it walks the snapshots backwards. At each step it repeats the
forward pass's decision ("did this path arrive from diagonal `k+1` or `k−1`?").
That tells it the previous point, so it can emit the snake's equal items and
the single insert or delete before them, in reverse order. Reversing that list
gives the edit script.

### What is the shortest edit script?

It is the list of operations returned by the engine:

```python
myers_diff("ABCABBA", "CBABAC")
# [('delete','A'), ('delete','B'), ('equal','C'), ('insert','B'),
#  ('equal','A'), ('equal','B'), ('delete','B'), ('equal','A'), ('insert','C')]
# D = 5 edits, the minimum possible (the example from Myers' paper)
```

When a block is replaced, deletions come before insertions. The classifier
relies on this conventional order.

### Complexity

| Case                 | Time                    | Space                                |
|----------------------|-------------------------|--------------------------------------|
| worst case           | `O((N + M) · D)`        | `O(N + M)` working + `O(D²)` snapshots |
| expected / typical   | `O(N + M + D²)`         | same                                 |

`N` and `M` are the sequence lengths, and `D` is the size of the shortest edit
script.

Two preprocessing steps cut the work. Neither changes the length of the
result, so it is still a shortest edit script:

1. **Common prefix and suffix trimming.** Unchanged regions at the start and
   end are never searched.
2. **Discarding unique items.** An item that occurs in only one of the two
   sequences can never be part of the LCS, so it is certainly an insertion or
   deletion. These items are set aside before the search and spliced back in
   afterwards, the same trick GNU diff uses. Two completely unrelated files
   therefore cost almost nothing.

Lines are mapped to small integers before the search, so the inner loop
compares integers instead of strings. Snapshots of `V` are stored as compact
machine-integer arrays.

## Architecture

```text
                 ┌──────────────────┐
                 │      CLI         │  cli.py: argparse, exit codes, no diff logic
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │   File Loader    │  parsers/__init__.py: registry by extension
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │ Parser/Normalizer│  parsers/text.py, parsers/notebook.py,
                 └────────┬─────────┘  core/normalizer.py (--ignore-*)
                          ▼
                 ┌──────────────────┐
                 │  Line Diff       │  core/line_diff.py
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │ Myers Algorithm  │  core/myers.py  ◄───────────────┐
                 └────────┬─────────┘                                 │
                          ▼                                           │
                 ┌──────────────────┐                                 │
                 │   Classifier     │  core/classifier.py             │
                 └────────┬─────────┘                                 │
             ┌────────────┴────────────┐                              │
             ▼                         ▼                              │
        INSERT/DELETE              MODIFY ──► core/char_diff.py ──────┘
                                       │      (same Myers engine, characters)
                          ┌────────────┴────────────┐
                          ▼                         ▼
                 renderers/terminal.py      renderers/json_renderer.py
                 renderers/summary.py
                 renderers/theme.py (all colors live here)
```

```text
                 ONE MYERS ENGINE
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
       LINE-LEVEL            CHARACTER-LEVEL
          DIFF                    DIFF
             └─────────┬─────────┘
                       ▼
                 DIFFERENTIATER
```

Each layer depends only on the layers below it. The core never prints
anything, and renderers never compute diffs.

```text
Differentiater/
├── differentiater/
│   ├── __init__.py            version
│   ├── __main__.py            python -m differentiater
│   ├── cli.py                 argument parsing, exit codes
│   ├── engine.py              compare_files() / compare_documents() API
│   ├── errors.py              user-facing error types
│   ├── core/
│   │   ├── myers.py           the Myers O(ND) engine (generic)
│   │   ├── line_diff.py       Myers over lines + line numbers
│   │   ├── char_diff.py       Myers over characters
│   │   ├── classifier.py      INSERT / DELETE / MODIFY grouping
│   │   ├── normalizer.py      comparison keys for --ignore-* and EOF newline
│   │   └── patch.py           apply_operations() reconstruction check
│   ├── parsers/
│   │   ├── __init__.py        parser registry, load_document()
│   │   ├── text.py            decoding, newlines, binary detection
│   │   └── notebook.py        logical .ipynb parsing
│   ├── renderers/
│   │   ├── theme.py           semantic styles and symbols, console factory
│   │   ├── summary.py         banner and summary block
│   │   ├── terminal.py        Part A / Part B
│   │   └── json_renderer.py   --json
│   └── models/
│       ├── diff_result.py     DiffOperation, CharacterOperation, DiffSummary, DiffResult
│       └── document.py        LoadedDocument, ParseOptions, CompareOptions
├── tests/                     pytest suite
├── examples/                  sample file pairs
├── benchmarks/benchmark.py
├── README.md  LICENSE  pyproject.toml  requirements.txt  .gitignore
```

### Modification detection

Myers only produces `equal`, `delete` and `insert`. An edited line appears as
a deletion followed by an insertion. The classifier
([`core/classifier.py`](differentiater/core/classifier.py)) decides which of
those pairs are really modifications:

1. **Hunks.** The script is split into *change hunks*: maximal runs of
   deletions and insertions between two unchanged lines. Only a deletion and
   an insertion in the **same hunk** can be a modification, because they
   replace each other at the same position. A hunk with only insertions stays
   an `INSERTION`, and a hunk with only deletions stays a `DELETION`.
2. **Order-preserving alignment.** In a hunk with *p* deletions and *q*
   insertions, a small dynamic program chooses the best non-crossing pairing
   by line similarity. For example, it pairs `alpha = 1 → alpha = 10` and
   `beta = 2 → beta = 20` even when an unrelated new line was inserted above
   them.
3. **Confirmation with Myers.** Each candidate pair is diffed at character
   level. It counts as a modification only if
   `2 × matched_chars / (len(old) + len(new)) ≥ 0.4`. Unrelated replacements,
   such as `x = compute()` → `########`, stay as a deletion plus an
   insertion. The character diff computed here is attached to the
   modification, so it is never computed twice.

### Programmatic use

```python
from differentiater.engine import compare_files

result = compare_files("old.py", "new.py")
print(result.summary.modified)
for op in result.changes:
    print(op.operation, op.old_line_number, op.new_line_number)
```

## Supported File Types

Any text file works, including `.txt`, `.py`, `.java`, `.c`, `.cpp`, `.js`,
`.ts`, `.html`, `.css`, `.json`, `.md`, `.sql` and `.ipynb`. The test suite runs
the example pairs for `.py`, `.java`, `.txt`, `.json`, `.js`, `.cpp`, `.sql`,
`.md` and `.ipynb`.

The parser is chosen by file extension. Files without a dedicated parser are
read as plain text, and `--raw` forces plain text for every file. To add a
format, write a function `(path, data, options) -> LoadedDocument` and register
it:

```python
from differentiater.parsers import register_parser
register_parser(".csv", load_csv_document)
```

**Text handling:**

- Encodings: UTF-8, UTF-8 with BOM, and UTF-16/UTF-32 with a BOM. Other
  undecodable text falls back to Latin-1.
- Line endings: LF, CRLF and CR are normalized internally. If the two files use
  different conventions, the banner shows a note.
- A missing final newline counts as a difference (like Git) and is shown as
  `\ No newline at end of file`.
- Binary files (NUL bytes, or more than 30% control bytes) are rejected with
  `Error: binary files are not supported for text diff.`
- Control characters in a line, such as a stray `ESC`, are displayed escaped
  (`\x1b`) instead of being sent to your terminal. Tabs are shown as four
  spaces.

## Jupyter Notebook Support

A notebook is a JSON file, but diffing that JSON directly is noisy. Every run
changes `execution_count`, `outputs` and `metadata`, and every source line is
wrapped in quotes and escapes.

**By default**, `.ipynb` files are compared **logically**. Each notebook
becomes a readable sequence of cells:

```text
━━ Cell 1 [markdown] ━━
# Sales Analysis
Quarterly numbers.
━━ Cell 2 [code] ━━
import pandas as pd
df = pd.read_csv('sales.csv')
```

| Notebook field              | Default     | `--include-output` | `--raw`        |
|-----------------------------|-------------|--------------------|----------------|
| code cell source            | compared    | compared           | as JSON text   |
| markdown / raw cell source  | compared    | compared           | as JSON text   |
| cell outputs                | ignored     | compared (`[output] …` lines) | as JSON text |
| `execution_count`           | ignored     | ignored            | as JSON text   |
| notebook / cell `metadata`  | ignored     | ignored            | as JSON text   |

- Cell headers are matched by **cell type only**. Inserting a cell therefore
  does not make every later header (`Cell 3` → `Cell 4`) look modified.
- With `--include-output`, stream text, `text/plain` results and errors
  (`ValueError: …`) are compared. Rich outputs such as images are summarized
  by MIME type (`[output] <image/png>`).
- Line numbers in notebook mode refer to this logical view, not to lines of
  the `.ipynb` file. Use `--raw` to get file line numbers.
- A metadata-only change gives exit code `0` (identical) in logical mode and
  `1` in `--raw` mode.

```bash
differentiater old.ipynb new.ipynb                    # logical: sources only
differentiater old.ipynb new.ipynb --include-output   # sources + outputs
differentiater old.ipynb new.ipynb --raw              # raw JSON text
```

## JSON Output

```bash
differentiater old.py new.py --json
```

```json
{
  "format_version": 1,
  "file_a": "old.py",
  "file_b": "new.py",
  "identical": false,
  "options": { "ignore_space": false, "ignore_blank_lines": false },
  "files": {
    "a": { "path": "old.py", "lines": 16, "encoding": "utf-8",
           "line_ending": "LF", "has_final_newline": true, "kind": "text" },
    "b": { "...": "..." }
  },
  "summary": {
    "old_lines": 16, "new_lines": 18, "line_delta": 2,
    "inserted": 2, "deleted": 0, "modified": 6, "unchanged": 10,
    "total_changes": 8, "chars_inserted": 25, "chars_deleted": 10
  },
  "notes": [],
  "operations": [
    { "type": "equal", "old_line": 1, "new_line": 1,
      "old_text": "import os", "new_text": "import os" },
    { "type": "insert", "old_line": null, "new_line": 3,
      "old_text": null, "new_text": "import json" },
    { "type": "modify", "old_line": 6, "new_line": 7,
      "old_text": "    return a + b", "new_text": "    return a + b + c",
      "character_diff": [
        { "type": "equal",  "text": "    return a + b" },
        { "type": "insert", "text": " + c" }
      ] }
  ]
}
```

- `operations` contains **every** line, including unchanged ones, in order.
  Applying them to file A reproduces file B.
- `type` is one of `equal`, `insert`, `delete` or `modify`. Line numbers are
  1-based, and `null` means the line is absent on that side.
- `character_diff` is present only on `modify` operations. Its runs have type
  `equal`, `insert` or `delete`.
- Output is UTF-8. Non-ASCII text is not escaped.

## Exit Codes

| Code | Meaning                                                        |
|------|----------------------------------------------------------------|
| `0`  | Files are identical (after any requested normalization)        |
| `1`  | Files are different                                            |
| `2`  | Invalid usage or an error (missing file, binary file, bad notebook…) |

```bash
differentiater old.py new.py; echo $?      # 1
differentiater old.py old.py; echo $?      # 0
differentiater missing.py new.py; echo $?  # 2   Error: file not found: missing.py
```

Errors go to standard error as a single `Error: …` line, with no traceback.

## Examples

The [`examples/`](examples) folder has file pairs you can try:

```bash
differentiater examples/old.py examples/new.py
differentiater examples/old.java examples/new.java
differentiater examples/old.txt examples/new.txt --part A
differentiater examples/old.py examples/new.py --part B
differentiater examples/old.py examples/new.py --summary
differentiater examples/old.py examples/new.py --json
differentiater examples/old.py examples/new.py --context 5
differentiater examples/old.py examples/new.py --ignore-space
differentiater examples/old.json examples/new.json
differentiater examples/old.ipynb examples/new.ipynb
differentiater examples/old.ipynb examples/new.ipynb --include-output
differentiater examples/old.ipynb examples/new.ipynb --raw
```

`examples/old.txt` and `examples/new.txt` contain Hindi (`नमस्ते` →
`नमस्ते दुनिया`) and emoji, so you can see Unicode character diffs.

### Ignore options

- `--ignore-space` ignores **all** whitespace when comparing lines (like
  `diff -w`), so `x=1`, `x = 1` and `\tx  =  1` are equal. The displayed text is
  the original.
- `--ignore-blank-lines` leaves blank lines (empty or whitespace-only) out of
  the comparison. They do not appear as changes, and line numbers still refer to
  the original files.

These options only change how lines are compared. The files are never
modified.

## Testing

```bash
pip install -e ".[dev]"
pytest
```

The suite has 167 tests:

| File                       | Covers |
|----------------------------|--------|
| `tests/test_myers.py`      | empty and identical inputs, single and multiple insertions, deletions and replacements, repeated values, duplicate lines, large sequences, `max_edits`, unhashable items. Every result is checked to be **optimal**: `D = N + M − 2·LCS` against a reference LCS. |
| `tests/test_line_diff.py`  | identical, insertion-only, deletion-only, modification-only and mixed cases, empty files, ignore options, missing EOF newline, and the **reconstruction property** |
| `tests/test_char_diff.py`  | single-character insertions, deletions and replacements; prefix, suffix and middle changes; completely different strings; Hindi; emoji; tabs |
| `tests/test_classifier.py` | modification versus true insertion or deletion, hunk boundaries, uneven hunks, line-number ordering |
| `tests/test_notebook.py`   | same notebook, changed code or markdown cell, added or deleted cell, metadata-only and output-only changes, invalid notebooks, `--raw` |
| `tests/test_parsers.py`    | LF/CRLF/CR, BOMs, UTF-16, Latin-1 fallback, binary detection, empty files, files left unmodified |
| `tests/test_cli.py`        | exit codes 0/1/2, missing file, binary file, `--json`, `--part A/B`, `--summary`, `--no-color`, `--context`, marker alignment, every example file |

**Reconstruction property.** The most important correctness check is

```python
apply_operations(file_a, diff(file_a, file_b)) == file_b
```

`apply_operations` (in [`core/patch.py`](differentiater/core/patch.py))
checks every `equal`, `delete` and `modify` against the original and fails
loudly on any mismatch. It runs on hand-picked edge cases and on thousands of
**randomized** sequence pairs: random lines, characters, Unicode and emoji.
For each pair it also checks that `unchanged + deleted + modified == old_lines`
and `unchanged + inserted + modified == new_lines`.

The tests also confirm that both the line diff and the character diff call
the shared `myers_diff` engine.

## Performance

```bash
python benchmarks/benchmark.py
```

These are synthetic files in which about 1% of lines are modified, 0.5%
inserted and 0.5% deleted. The time covers the whole comparison (Myers,
classification and character diffs), measured with Python 3.11 on a desktop PC:

| Lines   | Changes | Time     |
|--------:|--------:|---------:|
| 100     | 3       | ~0.5 ms  |
| 1,000   | 20      | ~4 ms    |
| 10,000  | 200     | ~45 ms   |
| 100,000 | 1,982   | ~0.54 s  |

Stress cases on the same machine:

- two identical 100k-line files: about 0.3 s
- two unrelated 20k-line files: about 0.6 s
- two unrelated 5k-line files that share 30% boilerplate lines (`}`, blank
  lines): about 1.8 s, with peak memory around 10–36 MB in every case

## Limitations

- **Pure Python.** Diffing two very large files that differ almost
  everywhere while sharing many repeated lines is still `O((N+M)·D)`, and can
  take a while.
- **Characters are Unicode code points.** Hindi conjuncts and emoji with
  modifiers are made of several code points, so a character diff can split a
  visual glyph. Marker alignment uses terminal cell widths, but terminals
  render complex scripts inconsistently.
- **No move detection.** A block moved elsewhere shows up as a deletion plus
  an insertion.
- **Modification threshold.** Pairing relies on a 40% character-similarity
  threshold. Heavily rewritten lines appear as a deletion plus an insertion.
- **Very long lines.** If a modified line's character diff would need more
  than 2,000 edits, it is shown as "whole line replaced" to keep runtime
  bounded.
- **Notebooks.** Only textual outputs are compared, and cell attachments are
  ignored.
- `--ignore-space` is all-or-nothing. There is no "ignore whitespace amount"
  mode yet.

## Future Improvements

- Linear-space Myers ("middle snake") for huge, highly different inputs
- Patience or histogram diff as an alternative strategy, reusing the same
  output model
- Word-level diff mode (Myers over word tokens)
- Grapheme-cluster-aware character diffs
- Side-by-side terminal layout and HTML output
- Directory comparison
- Move detection for relocated blocks
- Parsers for CSV (cell-aware) and structural JSON

## License

MIT. See [LICENSE](LICENSE).
