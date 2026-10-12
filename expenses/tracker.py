"""Core business logic.

ExpenseTracker owns the data and enforces every rule: validated entries,
known categories, budgets and safe deletion. Each successful change is
saved immediately.
"""

import logging
from datetime import date
from decimal import Decimal

from . import validators as v
from .exceptions import (
    DuplicateError, NotFoundError, OperationNotAllowedError, StorageError, ValidationError,
)
from .formatting import rupees
from .models import (
    DEFAULT_EXPENSE_CATEGORIES, EXPENSE, INCOME, INCOME_CATEGORIES, KINDS, OVERALL,
    PAYMENT_METHODS, PROTECTED_CATEGORY, Transaction,
)

log = logging.getLogger("expenses")

MAX_CATEGORIES = 30
BUDGET_THRESHOLDS = (Decimal("0.8"), Decimal("1.0"))  # warn at 80% and 100%


class ExpenseTracker:
    def __init__(self, storage, today=date.today):
        self.storage = storage
        self._today = today  # injectable clock for tests
        data = storage.load()
        try:
            self.transactions = {t.txn_id: t for t in map(Transaction.from_dict, data["transactions"])}
            self.categories = list(data["categories"] or DEFAULT_EXPENSE_CATEGORIES)
            self.budgets = {k: Decimal(val) for k, val in (data["budgets"] or {}).items()}
        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            raise StorageError(f"Data file contains an invalid record: {exc}") from exc
        self.next_id = max([int(data.get("next_id", 1)), *[t + 1 for t in self.transactions]])

    def today(self):
        return self._today()

    def save(self):
        self.storage.save({
            "transactions": [t.to_dict() for t in sorted(self.transactions.values(), key=lambda t: t.txn_id)],
            "categories": self.categories,
            "budgets": {k: str(val) for k, val in self.budgets.items()},
            "next_id": self.next_id,
        })

    # ------------------------------------------------------------ categories
    def categories_for(self, kind):
        return list(INCOME_CATEGORIES) if kind == INCOME else list(self.categories)

    def _category(self, name, kind):
        return v.validate_choice(name, self.categories_for(kind),
                                 "Income source" if kind == INCOME else "Category")

    def add_category(self, name):
        name = v.validate_category_name(name)
        if any(c.lower() == name.lower() for c in self.categories + [OVERALL]):
            raise DuplicateError(f"Category '{name}' already exists.")
        if len(self.categories) >= MAX_CATEGORIES:
            raise OperationNotAllowedError(f"You can have at most {MAX_CATEGORIES} categories.")
        self.categories.append(name)
        self.save()
        return name

    def remove_category(self, name, move_to=None):
        """Remove a category. If expenses use it, they must be moved to another category."""
        name = self._category(name, EXPENSE)
        if name == PROTECTED_CATEGORY:
            raise OperationNotAllowedError(f"'{PROTECTED_CATEGORY}' is a built-in category and cannot be removed.")
        used = [t for t in self.transactions.values() if t.is_expense and t.category == name]
        if used and move_to is None:
            raise OperationNotAllowedError(
                f"{len(used)} expense(s) use '{name}'. Choose a category to move them to.")
        if used:
            target = self._category(move_to, EXPENSE)
            if target == name:
                raise ValidationError("Choose a different category to move the expenses to.")
            for t in used:
                t.category = target
        self.categories.remove(name)
        self.budgets.pop(name, None)
        self.save()
        return len(used)

    # ------------------------------------------------------------ transactions
    def add(self, kind, day, amount, category, description="", method="Cash", save=True):
        """Validate and record a transaction. Returns (transaction, budget_warnings)."""
        kind = v.validate_choice(kind, KINDS, "Type")
        txn = Transaction(
            txn_id=self.next_id,
            kind=kind,
            day=v.validate_date(day, self.today()),
            amount=v.validate_amount(amount),
            category=self._category(category, kind),
            description=v.validate_description(description),
            method=v.validate_choice(method or "Cash", PAYMENT_METHODS, "Payment method"),
        )
        before = self._budget_usage(txn.day, txn.category) if txn.is_expense else {}
        self.transactions[txn.txn_id] = txn
        self.next_id += 1
        if save:
            self.save()
        log.info("Added %s #%d: %s %s", kind, txn.txn_id, txn.amount, txn.category)
        warnings = self._crossed_thresholds(before, txn) if txn.is_expense else []
        return txn, warnings

    def add_expense(self, day, amount, category, description="", method="Cash"):
        return self.add(EXPENSE, day, amount, category, description, method)

    def add_income(self, day, amount, source, description="", method="Net Banking"):
        return self.add(INCOME, day, amount, source, description, method)

    def get(self, txn_id):
        txn_id = v.validate_positive_int(txn_id, "Transaction ID")
        try:
            return self.transactions[txn_id]
        except KeyError:
            raise NotFoundError(f"No transaction with ID {txn_id}.") from None

    def update(self, txn_id, day=None, amount=None, category=None, description=None, method=None):
        """Change any fields of a transaction; fields left as None are unchanged."""
        txn = self.get(txn_id)
        changes = {}
        if day is not None:
            changes["day"] = v.validate_date(day, self.today())
        if amount is not None:
            changes["amount"] = v.validate_amount(amount)
        if category is not None:
            changes["category"] = self._category(category, txn.kind)
        if description is not None:
            changes["description"] = v.validate_description(description)
        if method is not None:
            changes["method"] = v.validate_choice(method, PAYMENT_METHODS, "Payment method")
        if not changes:
            raise ValidationError("Nothing to change.")
        for field, value in changes.items():  # all fields validated before any is applied
            setattr(txn, field, value)
        self.save()
        return txn

    def delete(self, txn_id):
        txn = self.get(txn_id)
        del self.transactions[txn.txn_id]
        self.save()
        return txn

    def search(self, start=None, end=None, kind=None, category=None, min_amount=None,
               max_amount=None, text=None, method=None):
        """Filter transactions (all criteria optional, combined with AND); newest first."""
        if start and end and start > end:
            raise ValidationError("Start date must be on or before the end date.")
        if min_amount is not None and max_amount is not None and min_amount > max_amount:
            raise ValidationError("Minimum amount cannot be larger than the maximum amount.")
        text = (text or "").strip().lower()
        result = []
        for t in self.transactions.values():
            if (start and t.day < start) or (end and t.day > end):
                continue
            if kind and t.kind != kind:
                continue
            if category and t.category.lower() != category.lower():
                continue
            if method and t.method.lower() != method.lower():
                continue
            if (min_amount is not None and t.amount < min_amount) or \
                    (max_amount is not None and t.amount > max_amount):
                continue
            if text and text not in t.description.lower() and text not in t.category.lower():
                continue
            result.append(t)
        return sorted(result, key=lambda t: (t.day, t.txn_id), reverse=True)

    # ------------------------------------------------------------ budgets
    def set_budget(self, category, amount):
        """Monthly limit for a category, or for 'Overall' spending."""
        if str(category).strip().lower() == OVERALL.lower():
            category = OVERALL
        else:
            category = self._category(category, EXPENSE)
        self.budgets[category] = v.validate_amount(amount, "Budget")
        self.save()
        return category, self.budgets[category]

    def remove_budget(self, category):
        key = next((k for k in self.budgets if k.lower() == str(category).strip().lower()), None)
        if key is None:
            raise NotFoundError(f"No budget is set for '{category}'.")
        del self.budgets[key]
        self.save()
        return key

    def spent(self, start, end, category=None):
        return sum((t.amount for t in self.transactions.values()
                    if t.is_expense and start <= t.day <= end and (category is None or t.category == category)),
                   Decimal("0"))

    def _budget_usage(self, day, category):
        start, end = v.month_bounds(day.year, day.month)
        usage = {}
        for key in (category, OVERALL):
            if key in self.budgets:
                usage[key] = self.spent(start, end, None if key == OVERALL else key)
        return usage

    def _crossed_thresholds(self, before, txn):
        """Warnings for budgets this new expense pushed past 80% or 100%."""
        warnings = []
        for key, old in before.items():
            limit = self.budgets[key]
            new = old + txn.amount
            for threshold in reversed(BUDGET_THRESHOLDS):
                if old < limit * threshold <= new:
                    label = "budget exceeded" if threshold == 1 else "80% of budget used"
                    warnings.append(f"{key}: {label} for {txn.day:%B} "
                                    f"(spent {rupees(new)} of {rupees(limit)}).")
                    break
        return warnings
