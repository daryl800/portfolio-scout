# portfolio.py
import csv

from app.config import HOLDINGS_CSV
from app.models import Position

def load_holdings():
    positions = []
    if not HOLDINGS_CSV.exists():
        return positions

    with open(HOLDINGS_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = (row.get("symbol") or "").strip().upper()
            if not symbol:
                continue

            try:
                positions.append(
                    Position(
                        symbol=symbol,
                        shares=int(float(row.get("shares", 0) or 0)),
                        avg_price=float(row.get("avg_price", 0) or 0),
                        entry_date=(row.get("entry_date") or "").strip(),
                        currency=(row.get("currency") or "USD").strip().upper(),
                        market=(row.get("market") or "").strip().upper(),
                        notes=(row.get("notes") or "").strip(),
                    )
                )
            except Exception as e:
                print(f"Skip invalid holding row: {row} | error: {e}")

    return positions
