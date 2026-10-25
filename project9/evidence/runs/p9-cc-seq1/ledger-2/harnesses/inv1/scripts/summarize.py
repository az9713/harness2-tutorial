import csv
import sys
from decimal import Decimal


def parse_amount(s):
    s = s.strip().replace(",", "")
    if s.startswith("(") and s.endswith(")"):
        return -Decimal(s[1:-1])
    return Decimal(s)


with open(sys.argv[1], newline="") as source:
    rows = list(csv.DictReader(source))
total = sum(
    (parse_amount(r["amount"]) for r in rows if r.get("status", "").strip().lower() != "void"),
    Decimal(0),
)
print(f"Total: {total:.2f}")
