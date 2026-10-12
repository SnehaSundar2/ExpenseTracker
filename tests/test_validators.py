import unittest
from datetime import date
from decimal import Decimal

from expenses import validators as v
from expenses.exceptions import ValidationError

TODAY = date(2026, 10, 15)


class TestAmount(unittest.TestCase):
    def test_valid_formats(self):
        cases = {"1,250.50": "1250.50", "₹500": "500.00", "Rs. 99": "99.00", "INR 10.5": "10.50",
                 " 7 ": "7.00", "0.01": "0.01"}
        for text, expected in cases.items():
            self.assertEqual(v.validate_amount(text), Decimal(expected), text)
        self.assertEqual(v.validate_amount(Decimal("3")), Decimal("3.00"))

    def test_invalid(self):
        for bad in ["", "abc", "0", "-5", "10.555", "NaN", "Infinity", "20000000", "1.2.3", None]:
            with self.assertRaises(ValidationError, msg=bad):
                v.validate_amount(bad)


class TestDates(unittest.TestCase):
    def test_formats_and_words(self):
        for text in ["2026-10-01", "01-10-2026", "01/10/2026"]:
            self.assertEqual(v.validate_date(text, TODAY), date(2026, 10, 1), text)
        self.assertEqual(v.validate_date("Today", TODAY), TODAY)
        self.assertEqual(v.validate_date("yesterday", TODAY), date(2026, 10, 14))

    def test_invalid_dates(self):
        for bad in ["2026-10-16", "2026-02-30", "31/04/2026", "1999-12-31", "tomorrow", ""]:
            with self.assertRaises(ValidationError, msg=bad):
                v.validate_date(bad, TODAY)

    def test_month(self):
        self.assertEqual(v.validate_month("", TODAY), (2026, 10))
        for text in ["2026-09", "9-2026", "09/2026"]:
            self.assertEqual(v.validate_month(text, TODAY), (2026, 9), text)
        for bad in ["2026-13", "2026-11", "Sept", "1999-01"]:
            with self.assertRaises(ValidationError, msg=bad):
                v.validate_month(bad, TODAY)

    def test_month_bounds_handles_leap_years(self):
        self.assertEqual(v.month_bounds(2028, 2), (date(2028, 2, 1), date(2028, 2, 29)))


class TestText(unittest.TestCase):
    def test_category_name(self):
        self.assertEqual(v.validate_category_name("  pet   care "), "Pet care")
        self.assertEqual(v.validate_category_name("Kids & School"), "Kids & School")
        for bad in ["X", "Food!", "x" * 31, "123abc", ""]:
            with self.assertRaises(ValidationError, msg=bad):
                v.validate_category_name(bad)

    def test_description(self):
        self.assertEqual(v.validate_description(None), "")
        self.assertEqual(v.validate_description("  lunch   with  team "), "lunch with team")
        with self.assertRaises(ValidationError):
            v.validate_description("x" * 101)

    def test_choice_and_int(self):
        self.assertEqual(v.validate_choice("upi", ["Cash", "UPI"], "Method"), "UPI")
        with self.assertRaises(ValidationError):
            v.validate_choice("cheque", ["Cash", "UPI"], "Method")
        self.assertEqual(v.validate_positive_int(" 4 ", "ID"), 4)
        for bad in ["0", "x", "2.5"]:
            with self.assertRaises(ValidationError):
                v.validate_positive_int(bad, "ID")


if __name__ == "__main__":
    unittest.main()
