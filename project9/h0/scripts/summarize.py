import csv
import sys
from decimal import Decimal

with open(sys.argv[1], newline="") as source:
    rows = list(csv.DictReader(source))
total = sum((Decimal(r["amount"]) for r in rows if Decimal(r["amount"]) > 0), Decimal(0))
print(f"Total: {total:.2f}")
