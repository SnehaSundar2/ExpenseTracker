# Project Report: Expense Tracker

**Program:** Virtual Internship – Python Development, Skyrovix IT Solutions Pvt. Ltd.
**Project:** Expense Tracker
**Submitted by:** Sneha S (Intern ID: SKX-2026-6425)
**Due date:** 11 November 2026

---

## 1. Introduction

Many students and young professionals don't know where their money goes each month. Small
daily spends on food, transport and online shopping add up, and budgets kept in a notebook or
spreadsheet are rarely checked in time. This project is a Python command-line expense tracker
that records every expense and income, warns when budgets are nearly used up, and turns the
records into clear summaries and practical insights.

## 2. Objectives

1. Build a working expense tracker from clearly separated Python modules.
2. Validate every input so wrong amounts, dates or categories never enter the records.
3. Process the records into summaries, budget status, trends, comparisons and insights.
4. Handle errors (bad input, bad import files, damaged data files) without crashing or losing data.
5. Document the workflow and verify the behaviour with automated tests.

## 3. Tools and technologies

| Item | Used |
|---|---|
| Language | Python 3 (tested on 3.13) |
| Libraries | Standard library only: `decimal`, `datetime`, `calendar`, `dataclasses`, `json`, `csv`, `collections`, `re`, `logging`, `argparse`, `unittest` |
| Storage | JSON file (atomic saves) |
| Testing | `unittest`, `unittest.mock` |

## 4. System design

### 4.1 Modules

| Module | Responsibility |
|---|---|
| `main.py` | Command-line options, demo data, report-only mode, starts the menu |
| `cli.py` | Menu, prompts, budget alerts, tables on screen |
| `validators.py` | Validates amounts, dates, months, categories, descriptions and choices |
| `models.py` | `Transaction` dataclass, default categories and payment methods |
| `tracker.py` | Business rules: transactions, categories, budgets and alerts |
| `storage.py` | Atomic JSON persistence and corrupt-file backup |
| `analysis.py` | Monthly summary, budget status, trend, comparison, projection, insights |
| `formatting.py` | ₹ formatting with Indian digit grouping |
| `reports.py` | Tables, text bar charts, monthly report |
| `csv_io.py` | CSV import with row-level error reporting, and export |
| `demo.py` | Realistic sample data for 3 months |
| `exceptions.py` | Custom error types |

### 4.2 Data model

**Transaction:** id, type (expense/income), date, amount (Decimal), category, description,
payment method.
**Budgets:** a monthly limit per category, plus an "Overall" limit.

### 4.3 Business rules

- Expense categories and income sources are separate lists, so "Salary" can't be an expense.
- A category used by existing expenses can only be removed by moving those expenses elsewhere.
  "Other" can never be removed.
- Budgets apply per calendar month. An alert is shown once, when spending first crosses 80% and
  again when it crosses 100%.
- Transaction IDs are never reused, even after deletion.

## 5. Implementation highlights

**Exact money with Decimal.** Floating-point numbers can't represent values like 0.1 exactly,
so totals drift (0.1 + 0.2 = 0.30000000000000004). All amounts use `Decimal` and are rounded to
paise, which a test verifies.

**Validation.** `validate_amount` accepts `₹1,250.50`, `Rs. 99` and `450`, and rejects
negatives, zero, more than 2 decimals, `NaN`, `Infinity` and amounts over ₹1 crore.
`validate_date` accepts several formats plus `today`/`yesterday`, and rejects impossible dates
(30 Feb) and future dates.

**Like-for-like comparison.** On 12 October, comparing 12 days of spending with all 30 days of
September would be misleading. So the insight compares this month so far with the *same number
of days* of last month.

**Fair projection.** A naive projection (spent ÷ days × days in month) treats a one-time rent
payment as if it repeats every few days. The tracker counts fixed costs (rent, bills,
education) once, and projects only day-to-day spending.

**Robust CSV import.** Each row is validated on its own. Bad rows are listed by line number and
reason, and the good rows are saved in one write:

```
Imported 6 transaction(s).
3 row(s) skipped:
  - Line 6: Amount 'abc' is not a valid number.
  - Line 7: Category must be one of: Food, Groceries, Transport, ...
  - Line 9: Amount must be greater than zero.
```

## 6. Testing

42 automated tests were written and **all pass**.

| # | Test case | Expected | Result |
|---|---|---|---|
| 1 | Amounts `1,250.50`, `₹500`, `Rs. 99` | Accepted as 1250.50, 500.00, 99.00 | Pass |
| 2 | Amounts `0`, `-5`, `10.555`, `NaN`, `abc` | ValidationError | Pass |
| 3 | Dates `30-02-2026`, tomorrow, `1999-12-31` | ValidationError | Pass |
| 4 | ₹0.10 added 3 times | Total exactly ₹0.30 | Pass |
| 5 | "Salary" as an expense, "Food" as income | Rejected | Pass |
| 6 | Edit with one invalid field | Nothing changed | Pass |
| 7 | Food budget ₹1,000: spend 700 → 850 → 900 → 1,100 → 1,110 | Alert at 850 (80%) and at 1,100 (100%) only | Pass |
| 8 | Remove a category in use | Refused, unless the expenses are moved | Pass |
| 9 | Projection with rent ₹6,000 and ₹3,000 day-to-day in 15 days | ₹12,200 (not ₹18,600) | Pass |
| 10 | CSV with bad amount, unknown category, future date, extra column | Those 4 rows skipped with line numbers; 3 good rows imported | Pass |
| 11 | CSV missing required columns / not UTF-8 / empty | DataFileError | Pass |
| 12 | Export then import into a new tracker | Same totals | Pass |
| 13 | Damaged data file | StorageError, backup created | Pass |
| 14 | Menu: invalid option, negative amount, future month | Error shown, menu continues | Pass |

## 7. Sample output (demo data)

```
  OCTOBER 2026
  Income ₹18,000.00   Expenses ₹15,985.00   Balance +₹2,015.00   Saved 11.2%

  SPENDING BY CATEGORY
  Rent                   ₹6,500.00   40.7%  ████████████████████████
  Shopping               ₹2,441.00   15.3%  █████████
  Food                   ₹1,497.00    9.4%  ██████

  INSIGHTS
  • Rent is your biggest expense: 40.7% of spending (₹6,500.00).
  • You spent 28.4% more than in the first 12 days of last month.
  • Over budget in: Shopping.
  • Weekends account for 42.4% of your day-to-day spending.
```

## 8. Challenges and solutions

| Challenge | Solution |
|---|---|
| Rounding errors with money | `Decimal` everywhere; amounts limited to 2 decimal places |
| Misleading mid-month comparisons | Compare the same number of days in both months |
| One-off rent inflating projections | Count fixed costs once, project day-to-day spending only |
| Repeated budget warnings on every expense | Alert only when a threshold is crossed |
| One bad row ruining a whole import | Validate rows individually; report line numbers; save once |
| Date-dependent features are hard to test | Injectable clock; tests use a fixed "today" |

## 9. Future enhancements

- Recurring expenses (rent, subscriptions) added automatically each month
- Charts with matplotlib, or a web dashboard (Flask)
- SQLite database for multi-year data
- Split expenses between friends
- Reminders when a budget reaches 80%

## 10. Conclusion

The Expense Tracker meets all project objectives. It is organised into focused modules,
validates every entry, turns raw transactions into useful summaries and insights, and handles
bad input and damaged files without losing data. The workflow is documented and the
behaviour is verified by 42 passing automated tests.

## 11. How to run

```bash
cd ExpenseTracker
python main.py --demo
python main.py --summary
python -m unittest discover -s tests -t . -v
```
