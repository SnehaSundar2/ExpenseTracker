"""Shared fixtures: a tracker on a temporary file with a fixed 'today'."""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from expenses.storage import JSONStorage
from expenses.tracker import ExpenseTracker

TODAY = date(2026, 10, 15)  # a Thursday


class TrackerTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.path = self.dir / "expenses.json"
        self.t = self.new_tracker()

    def new_tracker(self, path=None):
        return ExpenseTracker(JSONStorage(path or self.path), today=lambda: TODAY)

    def seed(self):
        """September and October data used by several tests."""
        add = self.t.add
        add("income", "2026-09-01", "20000", "Salary")
        add("expense", "2026-09-03", "6000", "Rent")
        add("expense", "2026-09-10", "2000", "Food")
        add("expense", "2026-09-20", "1000", "Transport")
        add("income", "2026-10-01", "20000", "Salary")
        add("expense", "2026-10-03", "6000", "Rent", "October rent", "Net Banking")
        add("expense", "2026-10-04", "1500", "Food", "Groceries and snacks", "UPI")   # Sunday
        add("expense", "2026-10-10", "1000", "Food", "Birthday dinner", "Card")       # Saturday
        add("expense", "2026-10-12", "500", "Transport", "Metro card", "UPI")
