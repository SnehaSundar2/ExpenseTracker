"""CSV import and export.

Import format (header row required; column order and case don't matter):

    date,type,amount,category,description,method
    2026-10-01,expense,250,Food,Lunch with friends,UPI

`type`, `description` and `method` are optional (type defaults to expense).
Bad rows are skipped and reported with their line number; the good rows
are still imported. A missing file or wrong header raises DataFileError.
"""

import csv
from pathlib import Path

from .exceptions import DataFileError, ExpenseError

REQUIRED = {"date", "amount", "category"}
EXPORT_COLUMNS = ["id", "date", "type", "amount", "category", "description", "method"]


def import_csv(tracker, path):
    """Returns (number_added, list_of_error_messages)."""
    path = Path(path)
    if not path.exists():
        raise DataFileError(f"File not found: {path}")
    added, errors = 0, []
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if not reader.fieldnames:
                raise DataFileError("The file is empty.")
            reader.fieldnames = [(h or "").strip().lower() for h in reader.fieldnames]
            missing = REQUIRED - set(reader.fieldnames)
            if missing:
                raise DataFileError(f"Missing column(s): {', '.join(sorted(missing))}. "
                                    f"Expected: date, type, amount, category, description, method.")
            for row in reader:
                line = reader.line_num
                if not any((value or "").strip() for value in row.values() if isinstance(value, str)):
                    continue
                if None in row:  # more cells than headers
                    errors.append(f"Line {line}: too many columns.")
                    continue
                try:
                    tracker.add(row.get("type") or "expense", row.get("date"), row.get("amount"),
                                row.get("category"), row.get("description") or "",
                                row.get("method") or "Cash", save=False)
                    added += 1
                except ExpenseError as exc:
                    errors.append(f"Line {line}: {exc}")
    except UnicodeDecodeError:
        raise DataFileError("File is not UTF-8 text. In Excel use 'Save As > CSV UTF-8'.") from None
    except OSError as exc:
        raise DataFileError(f"Could not read file: {exc}") from exc
    if added:
        tracker.save()  # one save for the whole import
    return added, errors


def export_csv(transactions, path):
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:  # BOM so Excel shows ₹ correctly
            writer = csv.writer(fh)
            writer.writerow(EXPORT_COLUMNS)
            for t in sorted(transactions, key=lambda t: (t.day, t.txn_id)):
                writer.writerow([t.txn_id, t.day.isoformat(), t.kind, f"{t.amount:.2f}", t.category,
                                 t.description, t.method])
    except OSError as exc:
        raise DataFileError(f"Could not write file: {exc}") from exc
    return path
