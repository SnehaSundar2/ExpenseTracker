# Expense Tracker

A menu-driven Python application for recording **expenses and income**, setting **monthly
budgets** with automatic alerts, and understanding where the money goes: monthly summaries,
category breakdowns, month-to-month comparisons, a 6-month trend and plain-English insights.

Built as a virtual internship project to demonstrate **Python modules, input validation,
data processing and error handling**. It uses only the Python standard library, so there is
nothing to install.

---

## 1. Features

| Area | What it does |
|---|---|
| **Record** | Add expenses and income with date, amount, category, description and payment method (Cash, UPI, Card, Net Banking, Wallet) |
| **Manage** | View recent transactions, search and filter, edit, delete (with confirmation) |
| **Categories** | 11 built-in expense categories, plus your own (up to 30); removing a used category moves its expenses safely |
| **Budgets** | Monthly limit per category and an **Overall** limit; alerts at **80%** and **100%** |
| **Monthly summary** | Income, expenses, balance, savings rate, daily average, biggest expense, spending by category and payment method |
| **Analysis** | Budget status with progress bars, comparison with last month, 6-month trend, top 5 expenses |
| **Insights** | e.g. "Rent is your biggest expense: 35%", "You spent 18% more than this time last month", projected month-end spending, weekend spending, savings |
| **Files** | Import a CSV (e.g. a bank statement), export everything to CSV (opens in Excel), save a full monthly report |
| **Safety** | Money stored as exact decimals, crash-safe saves, damaged data file backed up, activity log |

### Smart details

- **Exact money:** amounts use Python's `Decimal`, never `float`, so ₹0.10 + ₹0.20 is exactly
  ₹0.30.
- **Indian number format:** ₹1,23,456.50.
- **Flexible input:** `1,250.50`, `₹500` and `Rs. 99` are all accepted as amounts. Dates can be
  `2026-10-05`, `05-10-2026`, `05/10/2026`, `today` or `yesterday`.
- **Fair projection:** fixed monthly costs (rent, bills, education) are counted once, and only
  day-to-day spending is extended at its daily pace.
- **No alert spam:** each budget alert fires once, at the moment spending crosses 80% or 100%.

---

## 2. Project structure

```
ExpenseTracker/
├── main.py                    # Entry point: options, logging, demo data, report mode
├── expenses/                  # The application package
│   ├── __init__.py
│   ├── exceptions.py          # Custom exception hierarchy
│   ├── validators.py          # Amounts, dates, months, categories, text, choices
│   ├── models.py              # Transaction dataclass, default categories, payment methods
│   ├── storage.py             # Atomic JSON save/load, corrupt-file backup
│   ├── tracker.py             # Business rules: transactions, categories, budgets, alerts
│   ├── analysis.py            # Summaries, budgets, trend, comparison, projection, insights
│   ├── formatting.py          # ₹ formatting with Indian digit grouping
│   ├── reports.py             # Tables, bar charts, monthly report
│   ├── csv_io.py              # CSV import (row-level errors) and export
│   ├── demo.py                # 3 months of realistic sample data
│   └── cli.py                 # Interactive menu
├── sample_data/
│   └── bank_statement.csv     # Import example with 3 deliberately bad rows
├── tests/                     # 42 automated tests
└── docs/
    └── PROJECT_REPORT.md      # Internship submission report
```

---

## 3. How to run

Requires **Python 3.8 or newer**.

```bash
cd ExpenseTracker
python main.py --demo          # first run: loads 3 months of sample data, then opens the menu
python main.py                 # later runs: continues with your saved data
python main.py --summary       # print this month's full report and exit
python main.py --summary 2026-09 --report report_sept.txt
```

| Option | Purpose |
|---|---|
| `--data FILE` | Data file to use (default `data/expenses.json`) |
| `--demo` | Load 3 months of sample data (only into an empty tracker) |
| `--summary [YYYY-MM]` | Print the monthly report and exit (default: this month) |
| `--report PATH` | With `--summary`: also save the report to a file |

---

## 4. Workflow

```
  user input (menu / CSV row)
        │
        ▼
  validators ── invalid → "! Error: Amount can have at most 2 decimal places"  (nothing saved)
        │
        ▼
  tracker.add ── category must exist for its type (expense category vs income source)
        │        budget usage before/after compared → alert if 80% / 100% crossed
        ▼
  storage.save ── temp file + rename (crash-safe)
        │
        ▼
  analysis ──► monthly summary · budget status · comparison · trend · projection · insights
        │
        ▼
  reports / cli ──► tables and bar charts on screen · monthly report file · CSV export
```

### Typical session

1. **Add income** (2): stipend or salary for the month.
2. **Set budgets** (12): e.g. Overall ₹20,000, Food ₹4,500.
3. **Add expenses** (1) as you spend. The tracker warns when a budget hits 80% or 100%.
4. Check the **Monthly summary** (7), **Budget status** (8) and **Insights** (9).
5. **Compare with last month** (11) and look at the **6-month trend** (10).
6. **Export to CSV** (15) or **Save the monthly report** (16).

### Input rules

| Input | Rule | Examples |
|---|---|---|
| Amount | Positive, at most 2 decimals, max ₹1 crore; ₹ / Rs / commas allowed | `450`, `1,250.50`, `₹99` |
| Date | Not in the future, not before 2000 | `today`, `yesterday`, `2026-10-05`, `05-10-2026` |
| Month | `YYYY-MM`, `MM-YYYY` or `MM/YYYY`; not in the future | `2026-09` |
| Category | Must exist; matched case-insensitively; menu number or name | `3`, `food` |
| New category | 2–30 characters: letters, digits, spaces, `& ' -` | `Pet care` |
| Description | Optional, up to 100 characters | `Lunch with team` |
| CSV import | Header row with `date, amount, category` (+ optional `type, description, method`) | see `sample_data/` |

---

## 5. Key concepts demonstrated

**Python modules.** Each file has one responsibility. `tracker.py` holds the rules but never
prints, `analysis.py` only calculates, and `reports.py` and `cli.py` only present. So the same
analysis feeds the screen, the report file and the tests.

**Input validation.** Every value is cleaned and checked before it is stored. The checks cover
amount format and range, decimal places, real calendar dates (30 Feb is rejected), no future
dates, known categories for the right type, and valid payment methods. An edit validates
*all* new values before applying any of them.

**Data processing.**
- Grouping by category, payment method, month and weekday.
- Percentages, savings rate and daily average.
- Like-for-like month comparison: the first *N* days of this month against the first *N* days
  of last month.
- Projection that separates fixed from day-to-day costs.

**Error handling**
- Custom exceptions: `ExpenseError` → `ValidationError`, `NotFoundError`, `DuplicateError`,
  `OperationNotAllowedError`, `StorageError`, `DataFileError`.
- CSV import skips bad rows and reports each with its **line number** and reason.
- Saves are atomic, and a damaged data file is backed up (`.corrupt`) rather than overwritten.
- Deleting a category that expenses use is refused unless you choose where to move them.
- The menu shows friendly messages and logs unexpected errors to `expenses.log`.

---

## 6. Testing

```bash
cd ExpenseTracker
python -m unittest discover -s tests -t . -v
```

Result: **42 tests, all passing.** Tests use a temporary data file and a fixed "today"
(15 Oct 2026), so date-based results are always the same.

| Test file | Tests | Covers |
|---|---|---|
| `test_validators.py` | 9 | Amount formats and limits, NaN/Infinity, dates and words, invalid calendar dates, months, leap years, categories, descriptions |
| `test_tracker.py` | 15 | Add/edit/delete, exact decimals, persistence and IDs, search filters, categories (duplicates, safe removal), budgets, one-time 80%/100% alerts, per-month budgets, corrupt files |
| `test_analysis.py` | 9 | Monthly summary numbers, budget status, trend, comparison, projection, weekday pattern, insights, top expenses |
| `test_io_reports_cli.py` | 9 | ₹ formatting, CSV import with bad rows, header/encoding errors, export→import round trip, report sections, demo data, full menu sessions |
