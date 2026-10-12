"""Custom exception hierarchy.

Every deliberate error derives from ExpenseError so the CLI can catch a
single base class and show a friendly message instead of a traceback.
"""


class ExpenseError(Exception):
    """Base class for all expense tracker errors."""


class ValidationError(ExpenseError):
    """Raised when user input fails validation."""


class NotFoundError(ExpenseError):
    """Raised when a transaction or category does not exist."""


class DuplicateError(ExpenseError):
    """Raised when creating something that already exists."""


class OperationNotAllowedError(ExpenseError):
    """Raised when an action would leave the data inconsistent."""


class StorageError(ExpenseError):
    """Raised when the data file cannot be read or written."""


class DataFileError(ExpenseError):
    """Raised when an import/export CSV file is missing or badly structured."""
