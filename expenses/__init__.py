"""Expense Tracker.

A modular command-line expense tracker: records expenses and income,
validates every entry, tracks monthly budgets, and turns the data into
summaries, trends, insights and reports.
"""

import logging

__version__ = "1.0.0"

# Stay silent unless the application (main.py) configures logging.
logging.getLogger("expenses").addHandler(logging.NullHandler())
