"""Formatting helpers and the monthly text report."""

from datetime import datetime
from pathlib import Path

from . import analysis
from .exceptions import DataFileError
from .formatting import rupees
from .validators import month_bounds

BAR = "█"


def bar(value, maximum, width=24):
    if not maximum:
        return ""
    return BAR * max(1 if value else 0, round(width * float(value) / float(maximum)))


def format_table(rows, columns, right=()):
    if not rows:
        return "  Nothing to show."
    widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in columns}

    def cell(c, value):
        text = str(value)
        return text.rjust(widths[c]) if c in right else text.ljust(widths[c])

    lines = ["  " + "  ".join(cell(c, c.upper()) for c in columns),
             "  " + "  ".join("-" * widths[c] for c in columns)]
    lines += ["  " + "  ".join(cell(c, r.get(c, "")) for c in columns) for r in rows]
    return "\n".join(lines)


TXN_COLUMNS = ["id", "date", "type", "category", "amount", "method", "description"]


def txn_rows(transactions):
    return [{"id": t.txn_id, "date": t.day.strftime("%d %b %Y"), "type": t.kind.title(),
             "category": t.category, "amount": rupees(t.amount, sign=not t.is_expense),
             "method": t.method, "description": t.description or "-"} for t in transactions]


def summary_text(tracker, year, month):
    s = analysis.month_summary(tracker, year, month)
    lines = [f"  {s['label'].upper()}",
             f"  Income {rupees(s['income'])}   Expenses {rupees(s['expenses'])}   "
             f"Balance {rupees(s['net'], sign=True)}"
             + (f"   Saved {s['savings_rate']}%" if s["savings_rate"] is not None and s["net"] >= 0 else ""),
             f"  {s['count']} expense(s) · daily average {rupees(s['daily_average'])} over {s['days']} day(s)"]
    if s["biggest"]:
        b = s["biggest"]
        lines.append(f"  Biggest expense: {rupees(b.amount)} on {b.category}"
                     f"{' (' + b.description + ')' if b.description else ''}, {b.day:%d %b}")
    if s["by_category"]:
        lines += ["", "  SPENDING BY CATEGORY"]
        top = s["by_category"][0][1]
        width = max(len(c) for c, _, _ in s["by_category"])
        for cat, amount, share in s["by_category"]:
            lines.append(f"  {cat:<{width}}  {rupees(amount):>13}  {share:>5}%  {bar(amount, top)}")
    if s["by_method"]:
        lines += ["", "  BY PAYMENT METHOD"]
        lines += [f"  {m:<12} {rupees(a):>13}  {p:>5}%" for m, a, p in s["by_method"]]
    return "\n".join(lines)


def budget_text(tracker, year, month):
    rows = analysis.budget_status(tracker, year, month)
    if not rows:
        return "  No budgets set. Use 'Set or remove a budget' to add one."
    table = [{"budget for": r["category"], "limit": rupees(r["budget"]), "spent": rupees(r["spent"]),
              "left": rupees(r["remaining"]), "used": f"{r['used_pct']}%", "status": r["status"],
              "progress": bar(min(r["spent"], r["budget"]), r["budget"], 20).ljust(20, "·")} for r in rows]
    return format_table(table, ["budget for", "limit", "spent", "left", "used", "progress", "status"],
                        right={"limit", "spent", "left", "used"})


def trend_text(tracker, months=6):
    rows = analysis.monthly_trend(tracker, months)
    top = max((r["expenses"] for r in rows), default=0)
    lines = []
    for r in rows:
        lines.append(f"  {r['label']}  spent {rupees(r['expenses']):>13}  earned {rupees(r['income']):>13}"
                     f"  {bar(r['expenses'], top, 20)}")
    return "\n".join(lines)


def build_month_report(tracker, year, month):
    start, end = month_bounds(year, month)
    out = ["=" * 76, "  EXPENSE REPORT", f"  Generated {datetime.now():%d %b %Y, %H:%M}", "=" * 76, "",
           summary_text(tracker, year, month), "", "  BUDGETS", budget_text(tracker, year, month), "",
           "  INSIGHTS"]
    out += [f"  • {line}" for line in analysis.insights(tracker, year, month)]
    changes = analysis.compare_with_previous(tracker, year, month)
    if changes:
        out += ["", "  CHANGE VS PREVIOUS MONTH"]
        rows = [{"category": r["category"], "this month": rupees(r["this"]), "last month": rupees(r["previous"]),
                 "change": rupees(r["change"], sign=True),
                 "%": "new" if r["change_pct"] is None else f"{r['change_pct']}%"} for r in changes]
        out.append(format_table(rows, ["category", "this month", "last month", "change", "%"],
                                right={"this month", "last month", "change", "%"}))
    out += ["", "  TOP 5 EXPENSES",
            format_table(txn_rows(analysis.top_expenses(tracker, start, end)), TXN_COLUMNS, right={"amount"}),
            "", "  LAST 6 MONTHS", trend_text(tracker), "=" * 76]
    return "\n".join(out)


def save_report(tracker, year, month, path):
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(build_month_report(tracker, year, month) + "\n", encoding="utf-8")
    except OSError as exc:
        raise DataFileError(f"Could not write report: {exc}") from exc
    return path
