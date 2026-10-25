import csv
import sys
from decimal import Decimal


def parse_amount(raw):
    raw = raw.strip()
    negative = raw.startswith("(") and raw.endswith(")")
    if negative:
        raw = raw[1:-1]
    value = Decimal(raw)
    return -value if negative else value


with open(sys.argv[1], newline="") as source:
    rows = list(csv.DictReader(source))
total = sum(
    (parse_amount(r["amount"]) for r in rows if r["status"].strip().lower() != "void"),
    Decimal(0),
)
print(f"Total: {total:.2f}")
