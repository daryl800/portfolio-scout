# main_daily_profile.py
import csv
from dataclasses import asdict
from html import escape

from app.config import WATCHLIST_CSV, HOLDINGS_CSV, TOP_OPPORTUNITIES_N

from app.market_data import get_stock_metrics
from app.news import fetch_yahoo_news
from app.llm_analysis import analyze_stock_news,analyze_stock_news_batch
from app.models import Opportunity
from app.portfolio import load_holdings
from app.report import save_opportunities_csv, save_report_json, save_full_markdown_report, signal_bucket, why_flagged
from app.telegram_bot import send_telegram_message

from app.report import (
    save_opportunities_csv,
    save_report_json,
    save_full_markdown_report,
    split_telegram_text,
    signal_bucket,
)

from app.report import signal_bucket, why_flagged

from datetime import datetime
from html import escape



def load_watchlist():
    symbols = []
    if WATCHLIST_CSV.exists():
        with open(WATCHLIST_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = (row.get("symbol") or "").strip().upper()
                if symbol:
                    symbols.append(symbol)
    return list(dict.fromkeys(symbols))


def build_holding_rows_batch(positions):
    """
    批次處理 holdings：
    - 先對每檔抓 metrics + news
    - 再一次呼叫 analyze_stock_news_batch 拿分析結果
    """
    rows = []
    symbol_news_pairs = []

    # 先抓 metrics + news，暫存下來
    for p in positions:
        metrics = get_stock_metrics(p.symbol)
        if not metrics:
            continue

        news = fetch_yahoo_news(p.symbol, limit=3)
        symbol_news_pairs.append((p.symbol, news))

        rows.append({
            "symbol": p.symbol,
            "shares": p.shares,
            "avg_price": p.avg_price,
            "entry_date": p.entry_date,
            "currency": p.currency,
            "market": p.market,
            "notes": p.notes,
            "current_price": metrics.price,
            "score": metrics.score,
            # 先暫存 metrics / news，稍後填 analysis
            "metrics": metrics,
            "news": news,
        })

    # 批次呼叫 LLM 分析
    analysis_map = analyze_stock_news_batch(symbol_news_pairs)

    # 填回 pnl/analysis 等欄位
    for h in rows:
        metrics = h["metrics"]
        analysis = analysis_map.get(h["symbol"], None)

        if analysis is None:
            # 保險 fallback：用單檔版跑一次（理論上不太會碰到）
            analysis = analyze_stock_news(h["symbol"], h["news"])

        pnl_pct = (
            (metrics.price - h["avg_price"]) / h["avg_price"]
            if h["avg_price"] else 0.0
        )
        pnl_value = (metrics.price - h["avg_price"]) * h["shares"]

        h["pnl_pct"] = pnl_pct
        h["pnl_value"] = pnl_value
        h["analysis"] = analysis

    return rows



def build_opportunities(symbols):
    # 先抓 metrics + news，暫存
    rows = []
    symbol_news_pairs = []

    for symbol in symbols:
        metrics = get_stock_metrics(symbol)
        if not metrics:
            continue

        news = fetch_yahoo_news(symbol, limit=3)
        symbol_news_pairs.append((symbol, news))

        rows.append(
            {
                "symbol": symbol,
                "metrics": metrics,
                "news": news,
            }
        )

    # 批次呼叫 LLM 分析
    analysis_map = analyze_stock_news_batch(symbol_news_pairs)

    opportunities = []
    for row in rows:
        symbol = row["symbol"]
        metrics = row["metrics"]
        news = row["news"]

        analysis = analysis_map.get(symbol)
        if analysis is None:
            # 保險 fallback：若 batch 結果漏掉某檔，就退回單檔版
            analysis = analyze_stock_news(symbol, news)

        opportunities.append(
            Opportunity(
                symbol=symbol,
                metrics=metrics,
                news=news,
                analysis=analysis,
            )
        )

    # 排序 + 取前 N 名
    opportunities.sort(key=lambda x: x.metrics.score, reverse=True)
    return opportunities[:TOP_OPPORTUNITIES_N]



def build_summary(holding_rows, opportunities):
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = ["<b>Daily Stock Profile</b>", ""]

    if holding_rows:
        lines.append(f"<b>Holdings Review</b> ({now_text})")
        for h in holding_rows:
            symbol = escape(h["symbol"])
            market = escape(h["market"] or h["currency"])
            notes = escape(h["notes"] or "")
            sentiment = escape(h["analysis"].sentiment or "")
            action = escape(h["analysis"].action_label or "")
            short_view = escape(h["analysis"].short_term_view or "")
            long_view = escape(h["analysis"].long_term_view or "")
            risks = [escape(r) for r in (h["analysis"].risks or [])]

            pnl_pct_text = f"{h['pnl_pct'] * 100:+.1f}%"
            lines.append(
                f"<b>{symbol}</b> [{market}] | 持有 {h['shares']} 股 | 成本 {h['avg_price']:.2f} | "
                f"現價 {h['current_price']:.2f} | PnL {pnl_pct_text}"
            )
            if notes:
                lines.append(f"分類: {notes}")
            lines.append(f"情緒/動作: {sentiment} / {action}")
            lines.append(f"短期: {short_view}")
            lines.append(f"長期: {long_view}")
            if risks:
                lines.append(f"風險: {'；'.join(risks[:2])}")
            lines.append("")

    if opportunities:
        lines.append(f"<b>Watchlist / Opportunities</b> ({now_text})")
        for o in opportunities:
            symbol = escape(o.symbol)
            sentiment = escape(o.analysis.sentiment or "")
            action = escape(o.analysis.action_label or "")
            short_view = escape(o.analysis.short_term_view or "")
            long_view = escape(o.analysis.long_term_view or "")
            risks = [escape(r) for r in (o.analysis.risks or [])]

            bucket = signal_bucket(o.metrics.score, o.metrics.momentum_1m, o.metrics.macd_hist)

            lines.append(
                f"<b>{symbol}</b> | ${o.metrics.price:.2f} | score {o.metrics.score:.1f} | "
                f"{bucket} | {sentiment} | {action}"
            )
            lines.append(
                f"技術: 1M {o.metrics.momentum_1m*100:+.1f}% | Vol {o.metrics.volume_ratio:.2f}x | MACD {o.metrics.macd_hist:+.2f}"
            )
            lines.append(f"原因: {escape(why_flagged(o))}")
            lines.append(f"短期: {short_view}")
            lines.append(f"長期: {long_view}")
            if risks:
                lines.append(f"風險: {'；'.join(risks[:2])}")
            lines.append("")

    return "\n".join(lines)


def main():
    watchlist_symbols = load_watchlist()
    positions = load_holdings()

    print("WATCHLIST_CSV:", WATCHLIST_CSV)
    print("HOLDINGS_CSV:", HOLDINGS_CSV)
    print("watchlist_symbols:", watchlist_symbols)
    print("positions:", [p.symbol for p in positions])

    holding_symbols = [p.symbol for p in positions]
    watchlist_only = [s for s in watchlist_symbols if s not in set(holding_symbols)]

    print("watchlist_only:", watchlist_only)

    holding_rows = build_holding_rows_batch(positions)
    opportunities = build_opportunities(watchlist_only)

    print("holding_rows count:", len(holding_rows))
    print("opportunities count:", len(opportunities))

    save_opportunities_csv(opportunities)

    payload = {
        "holdings": [
            {
                "symbol": h["symbol"],
                "shares": h["shares"],
                "avg_price": h["avg_price"],
                "entry_date": h["entry_date"],
                "currency": h["currency"],
                "market": h["market"],
                "notes": h["notes"],
                "current_price": h["current_price"],
                "score": h["score"],
                "pnl_pct": h["pnl_pct"],
                "pnl_value": h["pnl_value"],
                "metrics": asdict(h["metrics"]),
                "analysis": asdict(h["analysis"]),
                "news": [asdict(n) for n in h["news"]],
            }
            for h in holding_rows
        ],
        "opportunities": [
            {
                "symbol": o.symbol,
                "metrics": asdict(o.metrics),
                "analysis": asdict(o.analysis),
                "news": [asdict(n) for n in o.news],
            }
            for o in opportunities
        ]
    }

    print("payload holdings:", len(payload["holdings"]))
    print("payload opportunities:", len(payload["opportunities"]))

    save_report_json(payload)

    summary = build_summary(holding_rows, opportunities)
    print("summary preview:\n", summary[:500])

    save_full_markdown_report(summary, opportunities)

    chunks = split_telegram_text(summary)
    ok = True
    msg = "ok"

    for chunk in chunks:
        ok, msg = send_telegram_message(chunk)
        if not ok:
            break

    print("Done.")


if __name__ == "__main__":
    main()
