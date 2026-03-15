# models.py
from dataclasses import dataclass, field
from typing import List

@dataclass
class NewsItem:
    title: str
    summary: str = ""
    published: str = ""

@dataclass
class StockMetrics:
    symbol: str
    price: float
    momentum_1m: float
    volume_ratio: float
    macd_hist: float
    atr: float = 0.0
    score: float = 0.0

@dataclass
class LLMAnalysis:
    sentiment: str = "中性"
    short_term_view: str = ""
    long_term_view: str = ""
    risks: List[str] = field(default_factory=list)
    action_label: str = "watch"
    confidence: int = 50

@dataclass
class Opportunity:
    symbol: str
    metrics: StockMetrics
    news: List[NewsItem] = field(default_factory=list)
    analysis: LLMAnalysis = field(default_factory=LLMAnalysis)

@dataclass
class Position:
    symbol: str
    shares: int
    avg_price: float
    entry_date: str = ""
    currency: str = "USD"
    market: str = ""
    notes: str = ""
