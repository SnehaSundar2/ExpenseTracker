"""Data processing: monthly summaries, budgets, trends, comparisons and insights."""

import calendar
from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from .formatting import rupees
from .models import EXPENSE, INCOME, OVERALL
from .validators import month_bounds

ZERO = Decimal("0")
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
FIXED_CATEGORIES = {"Rent", "Bills & Utilities", "Education"}  # usually paid once a month


def pct(part, whole):
    if not whole:
        return ZERO
    return (Decimal(part) * 100 / Decimal(whole)).quantize(Decimal("0.1"), ROUND_HALF_UP)


def money(value):
    return Decimal(value).quantize(Decimal("0.01"), ROUND_HALF_UP)


def previous_month(year, month):
    return (year - 1, 12) if month == 1 else (year, month - 1)


def days_counted(tracker, year, month):
    """Days of the month that have happened so far (all of them for past months)."""
    today = tracker.today()
    if (year, month) == (today.year, today.month):
        return today.day
    return calendar.monthrange(year, month)[1]


def month_summary(tracker, year, month):
    start, end = month_bounds(year, month)
    txns = tracker.search(start=start, end=end)
    expenses = [t for t in txns if t.kind == EXPENSE]
    income = sum((t.amount for t in txns if t.kind == INCOME), ZERO)
    spent = sum((t.amount for t in expenses), ZERO)

    by_category = defaultdict(lambda: ZERO)
    by_method = defaultdict(lambda: ZERO)
    for t in expenses:
        by_category[t.category] += t.amount
        by_method[t.method] += t.amount
    days = days_counted(tracker, year, month)
    return {
        "year": year, "month": month, "label": date(year, month, 1).strftime("%B %Y"),
        "income": income,
        "expenses": spent,
        "net": income - spent,
        "savings_rate": pct(income - spent, income) if income else None,
        "count": len(expenses),
        "daily_average": money(spent / days) if days else ZERO,
        "days": days,
        "biggest": max(expenses, key=lambda t: t.amount, default=None),
        "by_category": [(c, a, pct(a, spent)) for c, a in sorted(by_category.items(), key=lambda kv: -kv[1])],
        "by_method": [(m, a, pct(a, spent)) for m, a in sorted(by_method.items(), key=lambda kv: -kv[1])],
    }


def budget_status(tracker, year, month):
    """One row per budget: spent, remaining, % used and a status label."""
    start, end = month_bounds(year, month)
    rows = []
    for category, limit in sorted(tracker.budgets.items(), key=lambda kv: (kv[0] != OVERALL, kv[0])):
        spent = tracker.spent(start, end, None if category == OVERALL else category)
        used = pct(spent, limit)
        status = "OVER BUDGET" if used > 100 else "NEAR LIMIT" if used >= 80 else "OK"
        rows.append({"category": category, "budget": limit, "spent": spent,
                     "remaining": limit - spent, "used_pct": used, "status": status})
    return rows


def monthly_trend(tracker, months=6):
    """Income and expenses for the last `months` months, oldest first."""
    today = tracker.today()
    year, month = today.year, today.month
    keys = []
    for _ in range(months):
        keys.append((year, month))
        year, month = previous_month(year, month)
    rows = []
    for y, m in reversed(keys):
        start, end = month_bounds(y, m)
        txns = tracker.search(start=start, end=end)
        spent = sum((t.amount for t in txns if t.kind == EXPENSE), ZERO)
        earned = sum((t.amount for t in txns if t.kind == INCOME), ZERO)
        rows.append({"label": date(y, m, 1).strftime("%b %Y"), "expenses": spent, "income": earned,
                     "net": earned - spent})
    while len(rows) > 1 and not rows[0]["expenses"] and not rows[0]["income"]:
        rows.pop(0)  # don't show empty months from before the first entry
    return rows


def compare_with_previous(tracker, year, month):
    """Per-category spending this month vs last month, biggest changes first."""
    this = dict((c, a) for c, a, _ in month_summary(tracker, year, month)["by_category"])
    prev = dict((c, a) for c, a, _ in month_summary(tracker, *previous_month(year, month))["by_category"])
    rows = []
    for category in set(this) | set(prev):
        now, before = this.get(category, ZERO), prev.get(category, ZERO)
        rows.append({"category": category, "this": now, "previous": before, "change": now - before,
                     "change_pct": pct(now - before, before) if before else None})
    return sorted(rows, key=lambda r: -abs(r["change"]))


def weekday_pattern(tracker, start, end, day_to_day_only=False):
    totals = {d: ZERO for d in WEEKDAYS}
    for t in tracker.search(start=start, end=end, kind=EXPENSE):
        if day_to_day_only and t.category in FIXED_CATEGORIES:
            continue
        totals[WEEKDAYS[t.day.weekday()]] += t.amount
    return totals


def projection(tracker, year, month):
    """Projected month-end spending (current month only).

    Fixed monthly costs (rent, bills, fees) are paid once, so they are counted
    as they are; only day-to-day spending is extended at its current daily pace.
    """
    today = tracker.today()
    if (year, month) != (today.year, today.month):
        return None
    start, end = month_bounds(year, month)
    txns = tracker.search(start=start, end=end, kind=EXPENSE)
    fixed = sum((t.amount for t in txns if t.category in FIXED_CATEGORIES), ZERO)
    variable = sum((t.amount for t in txns if t.category not in FIXED_CATEGORIES), ZERO)
    days_in_month = calendar.monthrange(year, month)[1]
    return money(fixed + variable / today.day * days_in_month)


def top_expenses(tracker, start, end, n=5):
    return sorted(tracker.search(start=start, end=end, kind=EXPENSE), key=lambda t: -t.amount)[:n]


def insights(tracker, year, month):
    """Plain-English observations about the month."""
    s = month_summary(tracker, year, month)
    found = []
    if not s["count"]:
        return ["No expenses recorded for this month yet."]

    cat, amount, share = s["by_category"][0]
    found.append(f"{cat} is your biggest expense: {share}% of spending ({rupees(amount)}).")

    prev = month_summary(tracker, *previous_month(year, month))
    if prev["expenses"]:
        days = s["days"]
        # compare like-for-like: this month so far vs the same number of days last month
        py, pm = previous_month(year, month)
        pstart, _ = month_bounds(py, pm)
        pdays = min(days, calendar.monthrange(py, pm)[1])
        prev_same = tracker.spent(pstart, date(py, pm, pdays))
        if prev_same:
            change = pct(s["expenses"] - prev_same, prev_same)
            direction = "more" if change > 0 else "less"
            found.append(f"You spent {abs(change)}% {direction} than in the first {pdays} days of last month.")

    proj = projection(tracker, year, month)
    overall = tracker.budgets.get(OVERALL)
    if proj is not None:
        line = f"At this pace you will spend about {rupees(proj)} this month"
        if overall:
            line += " — over your overall budget." if proj > overall else " — within your overall budget."
        found.append(line + ("" if overall else "."))

    over = [r["category"] for r in budget_status(tracker, year, month) if r["status"] == "OVER BUDGET"]
    if over:
        found.append(f"Over budget in: {', '.join(over)}.")

    start, end = month_bounds(year, month)
    pattern = weekday_pattern(tracker, start, end, day_to_day_only=True)
    weekend, everyday = pattern["Sat"] + pattern["Sun"], sum(pattern.values(), ZERO)
    if everyday and weekend / everyday > Decimal("0.4"):  # 2 of 7 days is ~29%, so 40%+ stands out
        found.append(f"Weekends account for {pct(weekend, everyday)}% of your day-to-day spending.")

    if s["savings_rate"] is not None:
        if s["net"] >= 0:
            found.append(f"You saved {s['savings_rate']}% of your income ({rupees(s['net'])}).")
        else:
            found.append(f"You spent {rupees(-s['net'])} more than you earned this month.")
    return found
