"""Command-line interface.  Parses arguments, runs the engine, picks a renderer.

No diff logic lives here.

Exit codes:
    0  files are identical (after any requested normalisation)
    1  files differ
    2  invalid usage or an error
"""

from __future__ import annotations

import argparse
import errno
import os
import sys
from typing import List, Optional, Sequence

from differentiater import __version__
from differentiater.engine import compare_files
from differentiater.errors import DifferentiaterError
from differentiater.models.document import CompareOptions, ParseOptions
from differentiater.renderers.json_renderer import render_json
from differentiater.renderers.terminal import DEFAULT_CONTEXT, TerminalRenderer
from differentiater.renderers.theme import make_console

EXIT_IDENTICAL = 0
EXIT_DIFFERENT = 1
EXIT_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="differentiater",
        description=(
            "Compare two text files and show exactly what changed, using a "
            "from-scratch implementation of Myers' diff algorithm."
        ),
        epilog="Exit status: 0 identical, 1 different, 2 error.",
    )
    parser.add_argument("file_a", help="original file (A)")
    parser.add_argument("file_b", help="changed file (B)")
    parser.add_argument(
        "--part", type=str.upper, choices=["A", "B"],
        help="show only Part A (line diff) or Part B (character diff)",
    )
    parser.add_argument("--summary", action="store_true", help="show the summary")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    parser.add_argument(
        "--context", type=_non_negative_int, default=DEFAULT_CONTEXT, metavar="N",
        help=f"unchanged context lines around changes (default {DEFAULT_CONTEXT})",
    )
    parser.add_argument(
        "--ignore-space", action="store_true",
        help="ignore all whitespace differences when comparing lines",
    )
    parser.add_argument(
        "--ignore-blank-lines", action="store_true",
        help="ignore blank lines when comparing",
    )
    parser.add_argument(
        "--raw", action="store_true",
        help="compare notebooks (and any other parsed format) as raw text",
    )
    parser.add_argument(
        "--include-output", action="store_true",
        help="include code-cell outputs when comparing notebooks",
    )
    parser.add_argument("--no-color", action="store_true", help="disable colored output")
    parser.add_argument(
        "--version", action="version", version=f"differentiater {__version__}"
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point.  Returns the process exit code."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit_request:  # --help, --version or a usage error
        return _exit_code(exit_request.code)

    _ensure_utf8_streams()
    try:
        return _run(args)
    except DifferentiaterError as error:
        return _fail(str(error))
    except KeyboardInterrupt:
        return _fail("interrupted")
    except (MemoryError, RecursionError) as error:
        return _fail(f"input too large to compare ({type(error).__name__})")
    except OSError as error:
        if _output_closed(error):
            # The reader went away (e.g. ``| head``); nothing left to report.
            _silence_stdout()
            return EXIT_ERROR
        return _fail(f"cannot write output: {error}")
    except Exception as error:  # last resort: never show a traceback
        return _fail(f"unexpected {type(error).__name__}: {error}")


def _run(args: argparse.Namespace) -> int:
    """Compare the files, render the result and return the exit code."""
    result = compare_files(
        args.file_a,
        args.file_b,
        parse_options=ParseOptions(raw=args.raw, include_output=args.include_output),
        compare_options=CompareOptions(
            ignore_space=args.ignore_space,
            ignore_blank_lines=args.ignore_blank_lines,
        ),
    )

    if args.json:
        sys.stdout.write(render_json(result) + "\n")
    else:
        renderer = TerminalRenderer(make_console(no_color=args.no_color), context=args.context)
        show_summary, parts = _sections(args)
        renderer.render(result, show_summary=show_summary, parts=parts)
    sys.stdout.flush()

    return EXIT_DIFFERENT if result.has_differences else EXIT_IDENTICAL


def _sections(args: argparse.Namespace) -> "tuple[bool, List[str]]":
    """Decide which sections to show.

    * no flags            -> summary + Part A + Part B
    * ``--part X``        -> only Part X
    * ``--summary``       -> only the summary
    * both                -> summary + Part X
    """
    if args.part is None and not args.summary:
        return True, ["A", "B"]
    return args.summary, [args.part] if args.part else []


def _non_negative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a non-negative integer, got {value!r}") from None
    if number < 0:
        raise argparse.ArgumentTypeError(f"expected a non-negative integer, got {value!r}")
    return number


def _fail(message: str) -> int:
    print(f"Error: {message}", file=sys.stderr)
    return EXIT_ERROR


def _exit_code(code: object) -> int:
    if code is None:
        return EXIT_IDENTICAL
    return code if isinstance(code, int) else EXIT_ERROR


def _ensure_utf8_streams() -> None:
    """Switch streams that cannot encode Unicode output to UTF-8.

    Redirected output on Windows (including to ``NUL``, which even reports
    itself as a TTY) defaults to a legacy code page that cannot encode
    box-drawing characters, Hindi or emoji.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None or _can_encode(stream, "═│—नम😀"):
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def _can_encode(stream: object, sample: str) -> bool:
    encoding = getattr(stream, "encoding", None) or "ascii"
    try:
        sample.encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


def _output_closed(error: OSError) -> bool:
    """A closed pipe is EPIPE on POSIX but EINVAL on Windows."""
    return isinstance(error, BrokenPipeError) or error.errno in (errno.EPIPE, errno.EINVAL)


def _silence_stdout() -> None:
    """Point stdout at devnull so interpreter shutdown cannot raise again."""
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
    except (OSError, ValueError, AttributeError):
        pass


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
