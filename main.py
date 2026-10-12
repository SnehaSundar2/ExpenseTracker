"""Entry point for the Expense Tracker.

Usage:
    python main.py                      # interactive menu
    python main.py --demo               # load 3 months of sample data first (empty tracker only)
    python main.py --summary            # print this month's report and exit
    python main.py --summary 2026-09 --report report.txt
"""

import argparse
import logging
import sys

from expenses import reports
from expenses import validators as v
from expenses.cli import ExpenseCLI
from expenses.demo import load_demo
from expenses.exceptions import ExpenseError
from expenses.storage import JSONStorage
from expenses.tracker import ExpenseTracker


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):  # show ₹ and █ correctly on Windows consoles
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Expense Tracker")
    parser.add_argument("--data", default="data/expenses.json", help="data file (default data/expenses.json)")
    parser.add_argument("--demo", action="store_true", help="load 3 months of sample data")
    parser.add_argument("--summary", nargs="?", const="", metavar="YYYY-MM",
                        help="print the monthly report and exit (default: this month)")
    parser.add_argument("--report", metavar="PATH", help="with --summary: also save the report to a file")
    args = parser.parse_args(argv)

    logging.basicConfig(filename="expenses.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    try:
        tracker = ExpenseTracker(JSONStorage(args.data))
        if args.demo:
            print(f"Loaded {load_demo(tracker)} sample transactions and 5 budgets.")
        if args.summary is not None:
            year, month = v.validate_month(args.summary, tracker.today())
            print(reports.build_month_report(tracker, year, month))
            if args.report:
                reports.save_report(tracker, year, month, args.report)
                print(f"\nReport saved to {args.report}")
            return 0
        ExpenseCLI(tracker).run()
    except ExpenseError as exc:
        print(f"Error: {exc}")
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nExiting. All changes are saved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
