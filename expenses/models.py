"""Data model: a Transaction, plus the default categories and payment methods."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

EXPENSE = "expense"
INCOME = "income"
KINDS = (EXPENSE, INCOME)

DEFAULT_EXPENSE_CATEGORIES = [
    "Food", "Groceries", "Transport", "Rent", "Bills & Utilities", "Shopping",
    "Education", "Health", "Entertainment", "Travel", "Other",
]
INCOME_CATEGORIES = ["Salary", "Stipend", "Pocket Money", "Freelance", "Gift", "Other Income"]
PAYMENT_METHODS = ["Cash", "UPI", "Card", "Net Banking", "Wallet"]
PROTECTED_CATEGORY = "Other"   # always exists, so expenses can be moved into it
OVERALL = "Overall"            # budget key for the whole month's spending


@dataclass
class Transaction:
    txn_id: int
    kind: str
    day: date
    amount: Decimal
    category: str
    description: str = ""
    method: str = "Cash"

    @property
    def is_expense(self):
        return self.kind == EXPENSE

    def to_dict(self):
        return {"id": self.txn_id, "kind": self.kind, "date": self.day.isoformat(),
                "amount": str(self.amount), "category": self.category,
                "description": self.description, "method": self.method}

    @classmethod
    def from_dict(cls, d):
        return cls(txn_id=int(d["id"]), kind=d["kind"], day=date.fromisoformat(d["date"]),
                   amount=Decimal(d["amount"]), category=d["category"],
                   description=d.get("description", ""), method=d.get("method", "Cash"))
