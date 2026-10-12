from datetime import date
from decimal import Decimal

from expenses.exceptions import (
    DuplicateError, NotFoundError, OperationNotAllowedError, StorageError, ValidationError,
)
from expenses.tracker import ExpenseTracker
from expenses.storage import JSONStorage
from tests.helpers import TrackerTest


class TestTransactions(TrackerTest):
    def test_add_expense_cleans_input(self):
        txn, warnings = self.t.add_expense("yesterday", "₹1,250.5", "food", "  team   lunch ", "upi")
        self.assertEqual((txn.txn_id, txn.amount, txn.category, txn.description, txn.method),
                         (1, Decimal("1250.50"), "Food", "team lunch", "UPI"))
        self.assertEqual(txn.day, date(2026, 10, 14))
        self.assertEqual(warnings, [])

    def test_categories_depend_on_type(self):
        self.t.add_income("today", "5000", "salary")
        with self.assertRaises(ValidationError):
            self.t.add_income("today", "5000", "Food")      # Food is not an income source
        with self.assertRaises(ValidationError):
            self.t.add_expense("today", "100", "Salary")    # Salary is not an expense category
        with self.assertRaises(ValidationError):
            self.t.add_expense("today", "100", "Pizza")

    def test_invalid_entry_is_not_saved(self):
        with self.assertRaises(ValidationError):
            self.t.add_expense("2026-12-01", "100", "Food")  # future date
        self.assertEqual(self.t.transactions, {})
        self.assertFalse(self.path.exists())

    def test_exact_decimal_totals(self):
        for _ in range(3):
            self.t.add_expense("today", "0.10", "Food")
        self.assertEqual(self.t.spent(date(2026, 10, 1), date(2026, 10, 31)), Decimal("0.30"))

    def test_persistence_and_ids(self):
        self.seed()
        self.t.delete(9)
        reloaded = self.new_tracker()
        self.assertEqual(len(reloaded.transactions), 8)
        self.assertEqual(reloaded.get(6).description, "October rent")
        txn, _ = reloaded.add_expense("today", "10", "Food")
        self.assertEqual(txn.txn_id, 10)  # ids are never reused

    def test_update_is_all_or_nothing(self):
        txn, _ = self.t.add_expense("today", "100", "Food", "snacks")
        with self.assertRaises(ValidationError):
            self.t.update(txn.txn_id, amount="250", category="Pizza")
        self.assertEqual((txn.amount, txn.category), (Decimal("100.00"), "Food"))
        self.t.update(txn.txn_id, amount="250", category="transport", description="cab")
        self.assertEqual(self.new_tracker().get(txn.txn_id).category, "Transport")
        with self.assertRaises(ValidationError):
            self.t.update(txn.txn_id)

    def test_get_and_delete_errors(self):
        with self.assertRaises(NotFoundError):
            self.t.get(99)
        with self.assertRaises(ValidationError):
            self.t.get("abc")

    def test_search(self):
        self.seed()
        food = self.t.search(category="food")
        self.assertEqual([t.txn_id for t in food], [8, 7, 3])  # newest first
        self.assertEqual(len(self.t.search(start=date(2026, 10, 1), kind="expense")), 4)
        self.assertEqual([t.txn_id for t in self.t.search(text="birthday")], [8])
        self.assertEqual(len(self.t.search(min_amount=Decimal("1000"), max_amount=Decimal("2000"))), 4)
        self.assertEqual([t.txn_id for t in self.t.search(method="upi")], [9, 7])
        with self.assertRaises(ValidationError):
            self.t.search(start=date(2026, 10, 5), end=date(2026, 10, 1))


class TestCategories(TrackerTest):
    def test_add_and_duplicates(self):
        self.assertEqual(self.t.add_category("pet care"), "Pet care")
        for dup in ["PET CARE", "food", "overall"]:
            with self.assertRaises(DuplicateError, msg=dup):
                self.t.add_category(dup)
        self.assertIn("Pet care", self.new_tracker().categories)

    def test_remove_rules(self):
        self.seed()
        self.t.set_budget("Transport", "800")
        with self.assertRaises(OperationNotAllowedError):
            self.t.remove_category("Transport")          # used by 2 expenses
        self.assertEqual(self.t.remove_category("transport", move_to="Other"), 2)
        self.assertEqual({t.category for t in self.t.search(text="metro")}, {"Other"})
        self.assertNotIn("Transport", self.t.budgets)    # its budget went with it
        with self.assertRaises(OperationNotAllowedError):
            self.t.remove_category("Other")
        self.assertEqual(self.t.remove_category("Travel"), 0)


class TestBudgets(TrackerTest):
    def test_set_remove_and_validate(self):
        self.assertEqual(self.t.set_budget("food", "3000"), ("Food", Decimal("3000.00")))
        self.assertEqual(self.t.set_budget("OVERALL", "20000")[0], "Overall")
        with self.assertRaises(ValidationError):
            self.t.set_budget("Pizza", "100")
        with self.assertRaises(ValidationError):
            self.t.set_budget("Food", "-1")
        self.assertEqual(self.t.remove_budget("food"), "Food")
        with self.assertRaises(NotFoundError):
            self.t.remove_budget("Food")

    def test_alerts_fire_once_when_crossing_80_and_100_percent(self):
        self.t.set_budget("Food", "1000")
        self.t.set_budget("Overall", "10000")
        self.assertEqual(self.t.add_expense("today", "700", "Food")[1], [])
        warn = self.t.add_expense("today", "150", "Food")[1]          # 850 -> crosses 80%
        self.assertEqual(len(warn), 1)
        self.assertIn("80% of budget used", warn[0])
        self.assertEqual(self.t.add_expense("today", "50", "Food")[1], [])  # 900: still under 100%
        warn = self.t.add_expense("today", "200", "Food")[1]          # 1100 -> crosses 100%
        self.assertIn("Food: budget exceeded", warn[0])
        self.assertEqual(self.t.add_expense("today", "10", "Food")[1], [])  # already over: no repeat
        warn = self.t.add_expense("today", "7000", "Rent")[1]         # overall 8110 -> crosses 80%
        self.assertTrue(warn[0].startswith("Overall: 80%"))

    def test_budget_is_per_month(self):
        self.t.set_budget("Food", "1000")
        self.t.add_expense("2026-09-30", "990", "Food")
        self.assertEqual(self.t.add_expense("2026-10-01", "100", "Food")[1], [])


class TestStorageErrors(TrackerTest):
    def test_corrupt_file_backed_up(self):
        self.path.write_text("{oops", encoding="utf-8")
        with self.assertRaises(StorageError):
            self.new_tracker()
        self.assertTrue(self.path.with_suffix(".json.corrupt").exists())

    def test_invalid_record(self):
        self.path.write_text('{"transactions": [{"id": 1, "kind": "expense", "date": "bad", '
                             '"amount": "5", "category": "Food"}]}', encoding="utf-8")
        with self.assertRaises(StorageError):
            ExpenseTracker(JSONStorage(self.path))
