"""User-facing errors.  The CLI prints ``Error: <message>`` and exits with 2."""


class DifferentiaterError(Exception):
    """Base class for every expected, user-facing failure."""


class InputFileNotFoundError(DifferentiaterError):
    def __init__(self, path: str) -> None:
        super().__init__(f"file not found: {path}")
        self.path = path


class NotAFileError(DifferentiaterError):
    def __init__(self, path: str) -> None:
        super().__init__(f"not a regular file: {path}")
        self.path = path


class FileReadError(DifferentiaterError):
    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"cannot read {path}: {reason}")
        self.path = path


class BinaryFileError(DifferentiaterError):
    def __init__(self, path: str) -> None:
        super().__init__("binary files are not supported for text diff.")
        self.path = path


class InvalidNotebookError(DifferentiaterError):
    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"invalid notebook {path}: {reason}")
        self.path = path
