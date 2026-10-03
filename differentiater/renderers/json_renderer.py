"""Machine-readable JSON output."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from differentiater.models.diff_result import DiffOperation, DiffResult, FileInfo

JSON_FORMAT_VERSION = 1


def build_payload(result: DiffResult) -> Dict[str, Any]:
    """Convert a diff result into plain JSON-serialisable data."""
    summary = result.summary
    return {
        "format_version": JSON_FORMAT_VERSION,
        "file_a": result.old.path,
        "file_b": result.new.path,
        "identical": summary.is_identical,
        "options": {
            "ignore_space": result.ignore_space,
            "ignore_blank_lines": result.ignore_blank_lines,
        },
        "files": {"a": _file(result.old), "b": _file(result.new)},
        "summary": {
            "old_lines": summary.old_lines,
            "new_lines": summary.new_lines,
            "line_delta": summary.line_delta,
            "inserted": summary.inserted,
            "deleted": summary.deleted,
            "modified": summary.modified,
            "unchanged": summary.unchanged,
            "total_changes": summary.total_changes,
            "chars_inserted": summary.chars_inserted,
            "chars_deleted": summary.chars_deleted,
        },
        "notes": list(result.notes),
        "operations": [_operation(op) for op in result.operations],
    }


def render_json(result: DiffResult) -> str:
    """Serialise a diff result as pretty-printed UTF-8 JSON text."""
    return json.dumps(build_payload(result), indent=2, ensure_ascii=False)


def _file(info: FileInfo) -> Dict[str, Any]:
    return {
        "path": info.path,
        "lines": info.line_count,
        "encoding": info.encoding,
        "line_ending": info.line_ending,
        "has_final_newline": info.has_final_newline,
        "kind": info.kind,
    }


def _operation(op: DiffOperation) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "type": op.operation.value,
        "old_line": op.old_line_number,
        "new_line": op.new_line_number,
        "old_text": op.old_text,
        "new_text": op.new_text,
    }
    if op.char_operations is not None:
        data["character_diff"] = _characters(op)
    return data


def _characters(op: DiffOperation) -> List[Dict[str, str]]:
    return [
        {"type": char_op.operation.value, "text": char_op.text}
        for char_op in op.char_operations or []
    ]
