"""High-level pipeline: load -> normalise -> line diff -> classify -> result.

This is the programmatic API.  The CLI is a thin layer on top of it::

    from differentiater.engine import compare_files
    result = compare_files("old.py", "new.py")
    print(result.summary.modified)
"""

from __future__ import annotations

from typing import List, Optional

from differentiater.core.line_diff import diff_prepared
from differentiater.core.normalizer import prepare_lines
from differentiater.models.diff_result import DiffResult, DiffSummary, FileInfo
from differentiater.models.document import CompareOptions, LoadedDocument, ParseOptions
from differentiater.parsers import load_document


def compare_files(
    path_a: str,
    path_b: str,
    *,
    parse_options: Optional[ParseOptions] = None,
    compare_options: Optional[CompareOptions] = None,
) -> DiffResult:
    """Load and compare two files."""
    doc_a = load_document(path_a, parse_options)
    doc_b = load_document(path_b, parse_options)
    return compare_documents(doc_a, doc_b, compare_options)


def compare_documents(
    doc_a: LoadedDocument,
    doc_b: LoadedDocument,
    options: Optional[CompareOptions] = None,
) -> DiffResult:
    """Compare two already-loaded documents."""
    options = options or CompareOptions()
    old = prepare_lines(
        doc_a.lines, doc_a.keys, has_final_newline=doc_a.has_final_newline, options=options
    )
    new = prepare_lines(
        doc_b.lines, doc_b.keys, has_final_newline=doc_b.has_final_newline, options=options
    )
    operations = diff_prepared(old, new)
    summary = DiffSummary.from_operations(operations, len(doc_a.lines), len(doc_b.lines))
    return DiffResult(
        old=_file_info(doc_a),
        new=_file_info(doc_b),
        operations=operations,
        summary=summary,
        ignore_space=options.ignore_space,
        ignore_blank_lines=options.ignore_blank_lines,
        notes=_notes(doc_a, doc_b, options),
    )


def _file_info(doc: LoadedDocument) -> FileInfo:
    return FileInfo(
        path=doc.path,
        line_count=len(doc.lines),
        encoding=doc.encoding,
        line_ending=doc.line_ending,
        has_final_newline=doc.has_final_newline,
        kind=doc.kind,
    )


def _notes(doc_a: LoadedDocument, doc_b: LoadedDocument, options: CompareOptions) -> List[str]:
    """Human-readable remarks about how the comparison was performed."""
    notes = []
    if "notebook" in (doc_a.kind, doc_b.kind):
        notes.append("notebooks compared logically (cell sources); use --raw for JSON")
    endings = {doc_a.line_ending, doc_b.line_ending} - {"none"}
    if len(endings) > 1:
        notes.append(
            f"line endings differ ({doc_a.line_ending} vs {doc_b.line_ending}); "
            "normalized for comparison"
        )
    if doc_a.encoding != doc_b.encoding:
        notes.append(f"encodings differ ({doc_a.encoding} vs {doc_b.encoding})")
    if options.ignore_space:
        notes.append("whitespace ignored for comparison")
    if options.ignore_blank_lines:
        notes.append("blank lines ignored for comparison")
    return notes
