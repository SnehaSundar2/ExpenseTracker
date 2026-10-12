"""JSON file persistence.

Saves are atomic (write a temp file, then rename) so a crash mid-save
can never leave a half-written file. A corrupted file is backed up and
reported instead of being silently overwritten.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path

from .exceptions import StorageError

EMPTY = {"transactions": [], "categories": None, "budgets": {}, "next_id": 1}


class JSONStorage:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            return dict(EMPTY)
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            backup = self.path.with_suffix(self.path.suffix + ".corrupt")
            shutil.copyfile(self.path, backup)
            raise StorageError(f"Data file is damaged ({exc.msg}, line {exc.lineno}). "
                               f"A backup copy was saved as {backup.name}.") from exc
        except OSError as exc:
            raise StorageError(f"Could not read data file: {exc}") from exc
        if not isinstance(data, dict) or not isinstance(data.get("transactions", []), list):
            raise StorageError("Data file has an unexpected structure.")
        return {**EMPTY, **data}

    def save(self, data):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)
        except OSError as exc:
            raise StorageError(f"Could not save data file: {exc}") from exc
