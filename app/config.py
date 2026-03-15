# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
CACHE_DIR = DATA_DIR / "cache"

for p in [DATA_DIR, OUTPUT_DIR, CACHE_DIR]:
    p.mkdir(parents=True, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

TOP_NEWS_N = int(os.getenv("TOP_NEWS_N", "3"))
TOP_OPPORTUNITIES_N = int(os.getenv("TOP_OPPORTUNITIES_N", "8"))
MIN_PRICE = float(os.getenv("MIN_PRICE", "3"))
MIN_AVG_VOLUME = int(os.getenv("MIN_AVG_VOLUME", "500000"))

WATCHLIST_CSV = DATA_DIR / "watchlist.csv"
HOLDINGS_CSV = DATA_DIR / "holdings.csv"
TRADES_CSV = DATA_DIR / "trades.csv"
REPORT_JSON = OUTPUT_DIR / "daily_profile.json"
REPORT_MD = OUTPUT_DIR / "daily_profile.md"
REPORT_CSV = OUTPUT_DIR / "opportunities.csv"
