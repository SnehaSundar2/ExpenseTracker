"""Money formatting shared by the tracker, reports and menu."""

from decimal import Decimal


def rupees(value, sign=False):
    """Indian digit grouping: 1234567.5 -> '₹12,34,567.50'."""
    value = Decimal(value).quantize(Decimal("0.01"))
    negative = value < 0
    whole, frac = f"{abs(value):.2f}".split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    prefix = "-" if negative else ("+" if sign and value > 0 else "")
    return f"{prefix}₹{whole}.{frac}"
