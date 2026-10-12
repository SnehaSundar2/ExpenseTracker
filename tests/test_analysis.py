from decimal import Decimal

from expenses import analysis
from expenses.validators import month_bounds
from tests.helpers import TrackerTest


class TestAnalysis(TrackerTest):
    def setUp(self):
        super().setUp()
        self.seed()

    def test_month_summary(self):
        s = analysis.month_summary(self.t, 2026, 10)
        self.assertEqual(s["income"], Decimal("20000"))
        self.assertEqual(s["expenses"], Decimal("9000"))
        self.assertEqual(s["net"], Decimal("11000"))
        self.assertEqual(s["savings_rate"], Decimal("55.0"))
        self.assertEqual(s["days"], 15)                          # current month: days so far
        self.assertEqual(s["daily_average"], Decimal("600.00"))
        self.assertEqual(s["biggest"].category, "Rent")
        self.assertEqual(s["by_category"][0], ("Rent", Decimal("6000"), Decimal("66.7")))
        self.assertEqual(analysis.month_summary(self.t, 2026, 9)["days"], 30)  # past month: all days

    def test_budget_status(self):
        self.t.set_budget("Food", "3000")       # 2500 spent -> 83% NEAR LIMIT
        self.t.set_budget("Transport", "400")   # 500 spent -> OVER
        self.t.set_budget("Overall", "20000")   # 9000 -> OK
        rows = {r["category"]: r for r in analysis.budget_status(self.t, 2026, 10)}
        self.assertEqual(rows["Food"]["status"], "NEAR LIMIT")
        self.assertEqual(rows["Transport"]["status"], "OVER BUDGET")
        self.assertEqual(rows["Transport"]["remaining"], Decimal("-100.00"))
        self.assertEqual(rows["Overall"]["status"], "OK")
        self.assertEqual(analysis.budget_status(self.t, 2026, 10)[0]["category"], "Overall")  # listed first

    def test_trend_skips_months_before_first_entry(self):
        rows = analysis.monthly_trend(self.t, 6)
        self.assertEqual([r["label"] for r in rows], ["Sep 2026", "Oct 2026"])
        self.assertEqual(rows[0]["expenses"], Decimal("9000"))

    def test_compare_with_previous_month(self):
        rows = {r["category"]: r for r in analysis.compare_with_previous(self.t, 2026, 10)}
        self.assertEqual(rows["Food"]["change"], Decimal("500"))
        self.assertEqual(rows["Food"]["change_pct"], Decimal("25.0"))
        self.assertEqual(rows["Transport"]["change_pct"], Decimal("-50.0"))

    def test_projection_counts_fixed_costs_once(self):
        # fixed: rent 6000; day-to-day: 3000 over 15 days -> 200/day * 31 = 6200
        self.assertEqual(analysis.projection(self.t, 2026, 10), Decimal("12200.00"))
        self.assertIsNone(analysis.projection(self.t, 2026, 9))

    def test_weekday_pattern(self):
        pattern = analysis.weekday_pattern(self.t, *month_bounds(2026, 10), day_to_day_only=True)
        self.assertEqual(pattern["Sun"], Decimal("1500"))
        self.assertEqual(pattern["Sat"], Decimal("1000"))
        self.assertEqual(sum(pattern.values()), Decimal("3000"))  # rent excluded

    def test_insights(self):
        self.t.set_budget("Overall", "10000")
        lines = analysis.insights(self.t, 2026, 10)
        text = " ".join(lines)
        self.assertIn("Rent is your biggest expense", text)
        self.assertIn("more than in the first 15 days of last month", text)
        self.assertIn("over your overall budget", text)
        self.assertIn("Weekends account for 83.3%", text)
        self.assertIn("You saved 55.0%", text)

    def test_insights_for_empty_month(self):
        self.assertEqual(analysis.insights(self.t, 2026, 8), ["No expenses recorded for this month yet."])

    def test_top_expenses(self):
        top = analysis.top_expenses(self.t, *month_bounds(2026, 10), n=2)
        self.assertEqual([t.amount for t in top], [Decimal("6000"), Decimal("1500")])
