"""Input validation helpers.

Each function returns a cleaned value or raises ValidationError with a
message that can be shown directly to the user. Money is always handled
as Decimal (never float) so totals are exact to the paisa.
"""

import calendar
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from .exceptions import ValidationError

MAX_AMOUNT = Decimal("10000000")      # ₹1 crore per transaction
MIN_DATE = date(2000, 1, 1)
DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y")
CATEGORY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9 &'-]*$")
MONTH_PATTERNS = [
    (re.compile(r"^(\d{4})-(\d{1,2})$"), ("year", "month")),
    (re.compile(r"^(\d{1,2})[-/](\d{4})$"), ("month", "year")),
]
MAX_DESCRIPTION = 100


def validate_non_empty(value, field):
    if value is None or not str(value).strip():
        raise ValidationError(f"{field} cannot be empty.")
    return " ".join(str(value).split())


def validate_amount(value, field="Amount"):
    """'1,250.50', '₹500', 'Rs. 99' -> Decimal('1250.50'). Must be positive, max 2 decimals."""
    if isinstance(value, Decimal):
        text = str(value)
    else:
        text = validate_non_empty(value, field)
        text = re.sub(r"^(₹|rs\.?|inr)\s*", "", text, flags=re.IGNORECASE).replace(",", "").strip()
    try:
        amount = Decimal(text)
    except InvalidOperation:
        raise ValidationError(f"{field} '{value}' is not a valid number.") from None
    if not amount.is_finite():
        raise ValidationError(f"{field} must be a normal number.")
    if amount <= 0:
        raise ValidationError(f"{field} must be greater than zero.")
    if amount > MAX_AMOUNT:
        raise ValidationError(f"{field} cannot be more than ₹1,00,00,000.")
    if amount != amount.quantize(Decimal("0.01")):
        raise ValidationError(f"{field} can have at most 2 decimal places (paise).")
    return amount.quantize(Decimal("0.01"))


def validate_date(value, today=None, field="Date"):
    """Accepts a date, 'today', 'yesterday', YYYY-MM-DD, DD-MM-YYYY or DD/MM/YYYY. No future dates."""
    today = today or date.today()
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        day = value
    else:
        text = validate_non_empty(value, field).lower()
        if text == "today":
            day = today
        elif text == "yesterday":
            day = today - timedelta(days=1)
        else:
            for fmt in DATE_FORMATS:
                try:
                    day = datetime.strptime(text, fmt).date()
                    break
                except ValueError:
                    continue
            else:
                raise ValidationError(f"{field} '{value}' is not valid. Use YYYY-MM-DD or DD-MM-YYYY "
                                      "(or 'today' / 'yesterday').")
    if day > today:
        raise ValidationError(f"{field} cannot be in the future ({day:%d %b %Y}).")
    if day < MIN_DATE:
        raise ValidationError(f"{field} cannot be before {MIN_DATE:%d %b %Y}.")
    return day


def validate_month(value, today=None):
    """'2026-10', '10-2026' or '10/2026' -> (2026, 10). Blank -> current month."""
    today = today or date.today()
    if value is None or not str(value).strip():
        return today.year, today.month
    text = str(value).strip()
    for pattern, order in MONTH_PATTERNS:
        match = pattern.match(text)
        if match:
            parts = dict(zip(order, map(int, match.groups())))
            year, month = parts["year"], parts["month"]
            if not 1 <= month <= 12:
                raise ValidationError(f"Month must be between 1 and 12, got {month}.")
            if (year, month) > (today.year, today.month):
                raise ValidationError("Month cannot be in the future.")
            if year < MIN_DATE.year:
                raise ValidationError(f"Year cannot be before {MIN_DATE.year}.")
            return year, month
    raise ValidationError(f"Month '{value}' is not valid. Use YYYY-MM, e.g. {today:%Y-%m}.")


def month_bounds(year, month):
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def validate_category_name(value):
    name = validate_non_empty(value, "Category")
    if not 2 <= len(name) <= 30:
        raise ValidationError("Category name must be 2-30 characters long.")
    if not CATEGORY_PATTERN.match(name):
        raise ValidationError("Category name may contain only letters, digits, spaces, & ' and -.")
    return name[0].upper() + name[1:]


def validate_description(value):
    """Optional free text; trimmed, max 100 characters, no control characters."""
    if value is None:
        return ""
    text = " ".join(str(value).split())
    if len(text) > MAX_DESCRIPTION:
        raise ValidationError(f"Description must be at most {MAX_DESCRIPTION} characters.")
    if any(ord(c) < 32 for c in text):
        raise ValidationError("Description contains invalid characters.")
    return text


def validate_choice(value, choices, field):
    """Case-insensitive match against a list of display names; returns the canonical name."""
    text = validate_non_empty(value, field).lower()
    for choice in choices:
        if choice.lower() == text:
            return choice
    raise ValidationError(f"{field} must be one of: {', '.join(choices)}.")


def validate_positive_int(value, field, maximum=None):
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a whole number.") from None
    if number < 1:
        raise ValidationError(f"{field} must be at least 1.")
    if maximum is not None and number > maximum:
        raise ValidationError(f"{field} must be at most {maximum}.")
    return number
