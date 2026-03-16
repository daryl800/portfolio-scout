# app/build_daily_profile_input.py
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import csv

from app.config import WATCHLIST_CSV, HOLDINGS_CSV
from app.market_data import get_stock_metrics
from app.portfolio import load_holdings
from app.models import StockMetrics


def load_watchlist_symbols() -> list[str]:
    symbols: list[str] = []
    if WATCHLIST_CSV.exists():
        with open(WATCHLIST_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = (row.get("symbol") or "").strip().upper()
                if symbol:
                    symbols.append(symbol)
    return list(dict.fromkeys(symbols))


def build_holdings_block():
    positions = load_holdings()
    holdings_out = []

    for p in positions:
        metrics = get_stock_metrics(p.symbol)
        if not metrics:
            print(f"[INPUT] skip holding {p.symbol}: no metrics")
            continue

        pnl_pct = (
            (metrics.price - p.avg_price) / p.avg_price
            if p.avg_price
            else 0.0
        )
        pnl_value = (metrics.price - p.avg_price) * p.shares

        holdings_out.append(
            {
                "symbol": p.symbol,
                "shares": p.shares,
                "avg_price": p.avg_price,
                "entry_date": p.entry_date,
                "currency": p.currency,
                "market": p.market,
                "notes": p.notes,
                "metrics": asdict(metrics),
                "pnl_pct": pnl_pct,
                "pnl_value": pnl_value,
            }
        )

    return holdings_out


def build_opportunities_block():
    holdings = load_holdings()
    holding_symbols = {p.symbol for p in holdings}

    watchlist_symbols = load_watchlist_symbols()
    watchlist_only = [s for s in watchlist_symbols if s not in holding_symbols]

    opps_out = []

    for symbol in watchlist_only:
        metrics = get_stock_metrics(symbol)
        if not metrics:
            print(f"[INPUT] skip opp {symbol}: no metrics")
            continue

        opps_out.append(
            {
                "symbol": symbol,
                "metrics": asdict(metrics),
                "notes": None,  # 如果未來有額外欄位可放這裡
            }
        )

    return opps_out


def main():
    base_dir = Path(__file__).resolve().parent.parent
    output_path = base_dir / "data" / "daily_profile_input.json"

    holdings_block = build_holdings_block()
    opps_block = build_opportunities_block()

    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "holdings": holdings_block,
        "opportunities": opps_block,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(
        f"[INPUT] written to {output_path} "
        f"(holdings={len(holdings_block)}, opps={len(opps_block)})"
    )


if __name__ == "__main__":
    main()
