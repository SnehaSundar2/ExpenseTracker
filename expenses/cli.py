"""Interactive menu-driven command-line interface.

All ExpenseError subclasses are caught and shown as friendly messages;
unexpected errors are logged and the menu keeps running.
"""

import logging
from decimal import Decimal

from . import analysis, csv_io, reports
from . import validators as v
from .exceptions import ExpenseError, ValidationError
from .formatting import rupees
from .models import EXPENSE, INCOME, OVERALL, PAYMENT_METHODS

log = logging.getLogger("expenses")

MENU = """
===================== EXPENSE TRACKER =====================
 RECORD                         ANALYSE
  1. Add expense                 7. Monthly summary
  2. Add income                  8. Budget status
  3. Recent transactions         9. Spending insights
  4. Search & filter            10. 6-month trend
  5. Edit a transaction         11. Compare with last month
  6. Delete a transaction
 SETTINGS                       FILES
 12. Set or remove a budget     14. Import from CSV
 13. Manage categories          15. Export to CSV
                                16. Save monthly report
  0. Exit
==========================================================="""


def ask(prompt):
    return input(f"  {prompt}: ").strip()


def confirm(prompt):
    return ask(f"{prompt} [y/N]").lower() in {"y", "yes"}


class ExpenseCLI:
    def __init__(self, tracker):
        self.t = tracker
        self.actions = {
            "1": self.add_expense, "2": self.add_income, "3": self.recent, "4": self.search,
            "5": self.edit, "6": self.delete, "7": self.summary, "8": self.budgets,
            "9": self.insights, "10": self.trend, "11": self.compare, "12": self.manage_budget,
            "13": self.manage_categories, "14": self.import_csv, "15": self.export_csv,
            "16": self.save_report,
        }

    def run(self):
        while True:
            print(MENU)
            today = self.t.today()
            start, end = v.month_bounds(today.year, today.month)
            print(f"  {today:%B %Y}: spent {rupees(self.t.spent(start, end))} · "
                  f"{len(self.t.transactions)} transaction(s) recorded")
            choice = ask("Choose an option")
            if choice == "0":
                print("  Goodbye! All changes are saved.")
                return
            action = self.actions.get(choice)
            if action is None:
                print("  ! Invalid option, please enter a number from the menu.")
                continue
            try:
                action()
            except ExpenseError as exc:
                log.warning("%s failed: %s", action.__name__, exc)
                print(f"  ! Error: {exc}")
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
            except Exception:  # safety net; the full traceback goes to the log file
                log.exception("Unexpected error in %s", action.__name__)
                print("  ! An unexpected error occurred. See expenses.log for details.")

    # ---------------------------------------------------------- helpers
    def ask_month(self):
        return v.validate_month(ask("Month YYYY-MM [this month]"), self.t.today())

    def pick(self, options, prompt):
        print("  " + "  ".join(f"{i}.{o}" for i, o in enumerate(options, 1)))
        answer = ask(prompt)
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]
        return answer  # typed name; validated by the tracker

    def show(self, txns, limit=None):
        txns = txns[:limit] if limit else txns
        print(reports.format_table(reports.txn_rows(txns), reports.TXN_COLUMNS, right={"amount"}))

    # ---------------------------------------------------------- record
    def _add(self, kind):
        amount = ask("Amount (₹)")
        category = self.pick(self.t.categories_for(kind), "Source (number or name)" if kind == INCOME
                             else "Category (number or name)")
        day = ask("Date [today] (YYYY-MM-DD, DD-MM-YYYY, yesterday)") or "today"
        description = ask("Description (optional)")
        method = self.pick(PAYMENT_METHODS, "Paid by [1 = Cash]" if kind == EXPENSE else "Received by [4]") \
            or ("Cash" if kind == EXPENSE else "Net Banking")
        txn, warnings = self.t.add(kind, day, amount, category, description, method)
        print(f"  Saved #{txn.txn_id}: {kind} of {rupees(txn.amount)} for {txn.category} on {txn.day:%d %b %Y}.")
        for w in warnings:
            print(f"  ⚠ Budget alert — {w}")

    def add_expense(self):
        self._add(EXPENSE)

    def add_income(self):
        self._add(INCOME)

    def recent(self):
        self.show(self.t.search(), limit=15)

    def search(self):
        raw_from, raw_to = ask("From date [any]"), ask("To date [any]")
        start = v.validate_date(raw_from, self.t.today(), "From date") if raw_from else None
        end = v.validate_date(raw_to, self.t.today(), "To date") if raw_to else None
        kind = ask("Type expense/income [both]").lower() or None
        if kind:
            kind = v.validate_choice(kind, (EXPENSE, INCOME), "Type")
        category = ask("Category [any]") or None
        raw_min, raw_max = ask("Minimum amount [none]"), ask("Maximum amount [none]")
        found = self.t.search(start, end, kind, category,
                              v.validate_amount(raw_min, "Minimum amount") if raw_min else None,
                              v.validate_amount(raw_max, "Maximum amount") if raw_max else None,
                              ask("Text in description [any]") or None)
        spent = sum((t.amount for t in found if t.is_expense), Decimal("0"))
        print(f"  {len(found)} match(es); expenses total {rupees(spent)}.")
        self.show(found)

    def edit(self):
        txn = self.t.get(ask("Transaction ID"))
        self.show([txn])
        print("  Press Enter to keep a value.")
        txn = self.t.update(txn.txn_id,
                            day=ask(f"Date [{txn.day:%Y-%m-%d}]") or None,
                            amount=ask(f"Amount [{txn.amount}]") or None,
                            category=ask(f"Category [{txn.category}]") or None,
                            description=ask(f"Description [{txn.description or '-'}]") or None,
                            method=ask(f"Payment method [{txn.method}]") or None)
        print(f"  Updated #{txn.txn_id}.")

    def delete(self):
        txn = self.t.get(ask("Transaction ID"))
        self.show([txn])
        if not confirm("Delete this transaction?"):
            print("  Cancelled. Nothing was deleted.")
            return
        self.t.delete(txn.txn_id)
        print(f"  Deleted #{txn.txn_id}.")

    # ---------------------------------------------------------- analyse
    def summary(self):
        print(reports.summary_text(self.t, *self.ask_month()))

    def budgets(self):
        print(reports.budget_text(self.t, *self.ask_month()))

    def insights(self):
        year, month = self.ask_month()
        for line in analysis.insights(self.t, year, month):
            print(f"  • {line}")

    def trend(self):
        print(reports.trend_text(self.t, 6))

    def compare(self):
        year, month = self.ask_month()
        rows = analysis.compare_with_previous(self.t, year, month)
        table = [{"category": r["category"], "this month": rupees(r["this"]), "last month": rupees(r["previous"]),
                  "change": rupees(r["change"], sign=True),
                  "%": "new" if r["change_pct"] is None else f"{r['change_pct']}%"} for r in rows]
        print(reports.format_table(table, ["category", "this month", "last month", "change", "%"],
                                   right={"this month", "last month", "change", "%"}))

    # ---------------------------------------------------------- settings
    def manage_budget(self):
        print(reports.budget_text(self.t, self.t.today().year, self.t.today().month))
        category = self.pick([OVERALL] + self.t.categories, "Budget for (number or name)")
        amount = ask("Monthly limit in ₹ (type 'remove' to delete this budget)")
        if amount.lower() == "remove":
            print(f"  Removed the budget for {self.t.remove_budget(category)}.")
            return
        name, limit = self.t.set_budget(category, amount)
        print(f"  Monthly budget for {name} set to {rupees(limit)}.")

    def manage_categories(self):
        print("  Categories: " + ", ".join(self.t.categories))
        action = ask("Add or remove? [add/remove]").lower()
        if action == "add":
            print(f"  Added category '{self.t.add_category(ask('New category name'))}'.")
        elif action == "remove":
            name = ask("Category to remove")
            try:
                self.t.remove_category(name)
                print(f"  Removed '{name}'.")
            except ExpenseError as exc:
                if "Choose a category" not in str(exc):
                    raise
                print(f"  {exc}")
                moved = self.t.remove_category(name, ask("Move them to category"))
                print(f"  Removed '{name}' and moved {moved} expense(s).")
        else:
            raise ValidationError("Please type 'add' or 'remove'.")

    # ---------------------------------------------------------- files
    def import_csv(self):
        added, errors = csv_io.import_csv(self.t, ask("CSV file to import"))
        print(f"  Imported {added} transaction(s).")
        if errors:
            print(f"  {len(errors)} row(s) skipped:")
            for e in errors[:20]:
                print(f"    - {e}")

    def export_csv(self):
        path = ask("File name [expenses.csv]") or "expenses.csv"
        csv_io.export_csv(self.t.transactions.values(), path)
        print(f"  Exported {len(self.t.transactions)} transaction(s) to {path}.")

    def save_report(self):
        year, month = self.ask_month()
        path = ask(f"File name [report_{year}-{month:02d}.txt]") or f"report_{year}-{month:02d}.txt"
        reports.save_report(self.t, year, month, path)
        print(f"  Report saved to {path}.")
