"""Realistic sample data (last 3 months) so the tracker can be demonstrated immediately."""

import random
from datetime import date, timedelta
from decimal import Decimal

from .exceptions import OperationNotAllowedError

DAILY = [  # (category, description, low, high, chance per day, method)
    ("Food", "Canteen lunch", 60, 180, 0.75, "UPI"),
    ("Food", "Tea and snacks", 20, 80, 0.5, "Cash"),
    ("Transport", "Metro / bus", 30, 90, 0.6, "UPI"),
    ("Transport", "Auto ride", 60, 220, 0.12, "Cash"),
    ("Food", "Dinner out", 250, 900, 0.07, "Card"),
    ("Entertainment", "Movie", 180, 450, 0.04, "UPI"),
    ("Shopping", "Clothes / accessories", 400, 2500, 0.03, "Card"),
    ("Health", "Pharmacy", 80, 600, 0.03, "UPI"),
]
MONTHLY = [  # (day of month, category, description, amount, method)
    (3, "Rent", "PG / hostel rent", 6500, "Net Banking"),
    (8, "Bills & Utilities", "Mobile recharge", 299, "UPI"),
    (10, "Bills & Utilities", "Electricity share", 650, "UPI"),
    (12, "Education", "Online course / books", 999, "Card"),
]
BUDGETS = {"Overall": 22000, "Food": 4500, "Transport": 2000, "Shopping": 2000, "Entertainment": 800}


def load_demo(tracker, months=3, seed=7):
    """Fill an empty tracker with sample transactions. Returns the number added."""
    if tracker.transactions:
        raise OperationNotAllowedError("Demo data can only be loaded into an empty tracker.")
    rng = random.Random(seed)
    today = tracker.today()
    first = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    for _ in range(months - 2):
        first = (first - timedelta(days=1)).replace(day=1)
    count = 0
    day = first
    while day <= today:
        if day.day == 1:
            tracker.add("income", day, 18000, "Stipend", "Monthly stipend", "Net Banking", save=False)
            count += 1
        if day.day == 15 and rng.random() < 0.6:
            tracker.add("income", day, rng.choice([1500, 2500, 3000]), "Freelance", "Freelance project",
                        "UPI", save=False)
            count += 1
        for dom, cat, desc, amount, method in MONTHLY:
            if day.day == dom:
                tracker.add("expense", day, amount, cat, desc, method, save=False)
                count += 1
        if day.weekday() == 6:  # weekly groceries on Sundays
            tracker.add("expense", day, rng.randint(350, 900), "Groceries", "Weekly groceries", "UPI", save=False)
            count += 1
        weekend = day.weekday() >= 5
        for cat, desc, low, high, chance, method in DAILY:
            boost = 1.6 if weekend and cat in ("Food", "Entertainment", "Shopping") else 1.0
            if rng.random() < chance * boost:
                amount = Decimal(rng.randint(low, high))
                tracker.add("expense", day, amount, cat, desc, method, save=False)
                count += 1
        day += timedelta(days=1)
    tracker.save()
    for category, amount in BUDGETS.items():
        tracker.set_budget(category, amount)
    return count
