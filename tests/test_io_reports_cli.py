"""CSV import/export, report formatting, demo data and end-to-end CLI sessions."""

import io
from contextlib import redirect_stdout
from decimal import Decimal
from unittest.mock import patch

from expenses import csv_io, reports
from expenses.cli import ExpenseCLI
from expenses.demo import load_demo
from expenses.exceptions import DataFileError, OperationNotAllowedError
from tests.helpers import TODAY, TrackerTest


class TestRupees(TrackerTest):
    def test_indian_grouping(self):
        cases = {"0": "₹0.00", "999": "₹999.00", "1000": "₹1,000.00", "123456.5": "₹1,23,456.50",
                 "12345678": "₹1,23,45,678.00", "-2500": "-₹2,500.00"}
        for value, expected in cases.items():
            self.assertEqual(reports.rupees(Decimal(value)), expected, value)
        self.assertEqual(reports.rupees(Decimal("50"), sign=True), "+₹50.00")


class TestCSV(TrackerTest):
    def write(self, text, name="in.csv"):
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_import_good_and_bad_rows(self):
        path = self.write("Date,Type,Amount,Category,Description,Method\n"
                          "2026-10-01,expense,250,Food,Lunch,UPI\n"              # line 2: ok
                          "02-10-2026,,120,Transport,,\n"                         # line 3: ok, type defaults
                          "2026-10-03,expense,abc,Food,Bad amount,UPI\n"          # line 4: bad amount
                          "2026-10-04,expense,100,Pizza,Unknown category,UPI\n"   # line 5: bad category
                          "\n"                                                    # line 6: blank, ignored
                          "2026-12-01,expense,100,Food,Future,UPI\n"              # line 7: future date
                          "2026-10-05,income,30000,Salary,October salary,Net Banking\n"  # line 8: ok
                          "2026-10-06,expense,1,200,Food,Unquoted comma,UPI\n")   # line 9: extra column
        added, errors = csv_io.import_csv(self.t, path)
        self.assertEqual(added, 3)
        self.assertEqual([e.split(":")[0] for e in errors], ["Line 4", "Line 5", "Line 7", "Line 9"])
        self.assertIn("not a valid number", errors[0])
        self.assertIn("too many columns", errors[3])
        self.assertEqual((self.t.get(2).kind, self.t.get(2).method), ("expense", "Cash"))
        self.assertEqual(len(self.new_tracker().transactions), 3)  # saved once at the end

    def test_header_and_file_errors(self):
        with self.assertRaises(DataFileError):
            csv_io.import_csv(self.t, self.dir / "missing.csv")
        with self.assertRaises(DataFileError):
            csv_io.import_csv(self.t, self.write("", "empty.csv"))
        with self.assertRaises(DataFileError) as ctx:
            csv_io.import_csv(self.t, self.write("when,how much\n2026-10-01,5\n", "hdr.csv"))
        self.assertIn("Missing column", str(ctx.exception))
        latin = self.dir / "latin.csv"
        latin.write_bytes("date,amount,category,description\n2026-10-01,5,Food,Caf\xe9\n".encode("latin-1"))
        with self.assertRaises(DataFileError):
            csv_io.import_csv(self.t, latin)

    def test_export_then_import_round_trip(self):
        self.seed()
        out = csv_io.export_csv(self.t.transactions.values(), self.dir / "out" / "all.csv")
        other = self.new_tracker(self.dir / "other.json")
        added, errors = csv_io.import_csv(other, out)
        self.assertEqual((added, errors), (9, []))
        self.assertEqual(other.spent(TODAY.replace(day=1), TODAY), self.t.spent(TODAY.replace(day=1), TODAY))


class TestReportsAndDemo(TrackerTest):
    def test_month_report_sections(self):
        self.seed()
        self.t.set_budget("Food", "2000")
        text = reports.build_month_report(self.t, 2026, 10)
        for part in ["OCTOBER 2026", "SPENDING BY CATEGORY", "BUDGETS", "OVER BUDGET", "INSIGHTS",
                     "CHANGE VS PREVIOUS MONTH", "TOP 5 EXPENSES", "LAST 6 MONTHS", "₹20,000.00"]:
            self.assertIn(part, text)

    def test_demo_data(self):
        count = load_demo(self.t)
        self.assertGreater(count, 100)
        self.assertTrue(all(t.day <= TODAY for t in self.t.transactions.values()))
        self.assertEqual(min(t.day for t in self.t.transactions.values()).month, 8)
        self.assertIn("Overall", self.t.budgets)
        with self.assertRaises(OperationNotAllowedError):
            load_demo(self.t)


def run_cli(tracker, inputs):
    out = io.StringIO()
    with patch("builtins.input", side_effect=inputs), redirect_stdout(out):
        ExpenseCLI(tracker).run()
    return out.getvalue()


class TestCLI(TrackerTest):
    def test_record_and_review_session(self):
        self.t.set_budget("Food", "500")
        out = run_cli(self.t, [
            "1", "450", "1", "", "Lunch", "2",     # expense: Food (option 1), today, UPI (option 2)
            "1", "100", "food", "yesterday", "", "",  # pushes Food over budget
            "2", "15000", "1", "2026-10-01", "Stipend", "",  # income: Salary (option 1)
            "3",                                    # recent
            "7", "",                                # this month's summary
            "6", "1", "y",                          # delete #1
            "0"])
        self.assertIn("Saved #1: expense of ₹450.00 for Food", out)
        self.assertIn("Budget alert — Food: 80% of budget used", out)
        self.assertIn("Budget alert — Food: budget exceeded", out)
        self.assertIn("Saved #3: income of ₹15,000.00 for Salary", out)
        self.assertIn("OCTOBER 2026", out)
        self.assertIn("Deleted #1.", out)
        self.assertEqual(len(self.new_tracker().transactions), 2)

    def test_errors_are_reported_not_raised(self):
        out = run_cli(self.t, [
            "42",                                   # bad menu option
            "1", "-50", "Food", "", "", "",         # negative amount
            "1", "50", "Pizza", "", "", "",         # unknown category
            "7", "2027-01",                         # future month
            "5", "99",                              # unknown transaction
            "0"])
        self.assertIn("Invalid option", out)
        self.assertIn("Amount must be greater than zero", out)
        self.assertIn("Category must be one of", out)
        self.assertIn("Month cannot be in the future", out)
        self.assertIn("No transaction with ID 99", out)
        self.assertEqual(self.t.transactions, {})

    def test_delete_can_be_cancelled(self):
        self.t.add_expense("today", "10", "Food")
        out = run_cli(self.t, ["6", "1", "n", "0"])
        self.assertIn("Nothing was deleted", out)
        self.assertEqual(len(self.t.transactions), 1)
