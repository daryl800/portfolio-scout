# llm_analysis.py
import json
from openai import OpenAI
from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.models import LLMAnalysis, NewsItem

client = OpenAI(api_key=OPENAI_API_KEY)

def analyze_stock_news(symbol: str, news_list: list[NewsItem]) -> LLMAnalysis:
    if not OPENAI_API_KEY:
        return LLMAnalysis(
            sentiment="中性",
            short_term_view="未設定 OPENAI_API_KEY，略過分析",
            long_term_view="未設定 OPENAI_API_KEY，略過分析",
            risks=["API key missing"],
            action_label="watch",
            confidence=20,
        )

    news_text = "\n".join(
        f"- {n.published} | {n.title} | {n.summary}"
        for n in news_list if n.title
    ) or "No important news found."

    prompt = f"""
你是一位謹慎的股票研究助理。請根據 {symbol} 的最新新聞做摘要。
請只輸出 JSON，不要輸出 markdown，不要加註解。

JSON schema:
{{
  "sentiment": "積極|中性|消極",
  "short_term_view": "一句話",
  "long_term_view": "一句話",
  "risks": ["風險1", "風險2"],
  "action_label": "watch|review|hold|avoid",
  "confidence": 0
}}

新聞如下：
{news_text}
""".strip()

    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content": "You are a careful financial research assistant. Reply in Traditional Chinese and valid JSON only."},
                {"role": "user", "content": prompt},
            ],
        )
        content = resp.choices[0].message.content.strip()
        data = json.loads(content)
        return LLMAnalysis(
            sentiment=data.get("sentiment", "中性"),
            short_term_view=data.get("short_term_view", ""),
            long_term_view=data.get("long_term_view", ""),
            risks=data.get("risks", []),
            action_label=data.get("action_label", "watch"),
            confidence=int(data.get("confidence", 50)),
        )
    except Exception as e:
        return LLMAnalysis(
            sentiment="中性",
            short_term_view=f"分析失敗: {e}",
            long_term_view="",
            risks=["LLM parsing failed"],
            action_label="watch",
            confidence=10,
        )
