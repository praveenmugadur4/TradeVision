"""
Market Pulse Engine — Live market context for smarter trading decisions.

1. India VIX (Fear Index) — market risk level
2. Nifty/Sensex Trend — don't fight the market
3. Analyst Recommendations — brokerage ratings from yfinance
4. News Sentiment — headline sentiment from financial RSS feeds
"""

import yfinance as yf
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timedelta
from .indicators import calculate_all_indicators

# ═══════════════════════════════════════════
# SENTIMENT WORD LISTS
# ═══════════════════════════════════════════
POSITIVE_WORDS = {
    'surge', 'surges', 'surging', 'rally', 'rallies', 'rallying',
    'breakout', 'bullish', 'upgrade', 'upgraded', 'outperform',
    'record', 'high', 'highs', 'gains', 'gain', 'soar', 'soars',
    'jumps', 'jump', 'boost', 'boosted', 'strong', 'strength',
    'buy', 'buying', 'accumulate', 'positive', 'profit', 'profits',
    'growth', 'growing', 'beats', 'beat', 'exceeds', 'exceeded',
    'optimistic', 'recovery', 'recovering', 'rebound', 'rebounds',
    'target', 'upside', 'overweight', 'revenue', 'dividend',
    'momentum', 'expansion', 'expand', 'outperformance', 'attractive',
}

NEGATIVE_WORDS = {
    'crash', 'crashes', 'crashing', 'fall', 'falls', 'falling',
    'bearish', 'downgrade', 'downgraded', 'underperform', 'sell',
    'selling', 'selloff', 'decline', 'declines', 'declining',
    'loss', 'losses', 'plunge', 'plunges', 'plunging', 'drops',
    'drop', 'tumble', 'tumbles', 'weak', 'weakness', 'warning',
    'fraud', 'scam', 'default', 'debt', 'risk', 'risky',
    'negative', 'concern', 'concerns', 'fear', 'fears', 'panic',
    'underweight', 'reduce', 'avoid', 'caution', 'cautious',
    'slump', 'slumps', 'correction', 'volatile', 'volatility',
    'miss', 'misses', 'missed', 'disappointing', 'poor',
}


def get_india_vix():
    """Fetch India VIX (fear index) — key market risk indicator."""
    try:
        vix = yf.Ticker("^INDIAVIX")
        hist = vix.history(period="5d")
        if hist.empty:
            return None

        current = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
        change = round(current - prev, 2)
        change_pct = round((change / prev) * 100, 2) if prev else 0

        # VIX interpretation
        if current < 12:
            level = "VERY_LOW"
            mood = "Extreme Greed — Market very calm, complacency risk"
            color = "#00E676"
        elif current < 15:
            level = "LOW"
            mood = "Low Fear — Favorable for buying"
            color = "#69F0AE"
        elif current < 20:
            level = "MODERATE"
            mood = "Normal — Balanced market conditions"
            color = "#FFD740"
        elif current < 25:
            level = "HIGH"
            mood = "Elevated Fear — Be cautious with new positions"
            color = "#FF9100"
        else:
            level = "VERY_HIGH"
            mood = "Extreme Fear — High risk, potential reversal zone"
            color = "#FF1744"

        return {
            "value": round(current, 2),
            "change": change,
            "change_pct": change_pct,
            "level": level,
            "mood": mood,
            "color": color,
        }
    except Exception as e:
        print(f"VIX fetch error: {e}")
        return None


def get_nifty_trend():
    """Analyze Nifty 50 trend — don't fight the market."""
    try:
        nifty = yf.Ticker("^NSEI")
        df = nifty.history(period="3mo")
        if df.empty or len(df) < 20:
            return None

        df_ind = calculate_all_indicators(df)
        latest = df_ind.iloc[-1]
        prev = df_ind.iloc[-2] if len(df_ind) > 1 else latest

        close = float(latest["Close"])
        prev_close = float(prev["Close"])
        change = round(close - prev_close, 2)
        change_pct = round((change / prev_close) * 100, 2) if prev_close else 0

        # Trend signals
        ema9 = float(latest.get("EMA_9", 0)) if pd.notna(latest.get("EMA_9")) else None
        ema21 = float(latest.get("EMA_21", 0)) if pd.notna(latest.get("EMA_21")) else None
        ema50 = float(latest.get("EMA_50", 0)) if pd.notna(latest.get("EMA_50")) else None
        rsi = float(latest.get("RSI", 50)) if pd.notna(latest.get("RSI")) else 50
        vwap = float(latest.get("VWAP", 0)) if pd.notna(latest.get("VWAP")) else None

        bullish = 0
        bearish = 0
        signals = []

        if ema9 and ema21:
            if ema9 > ema21:
                bullish += 1
                signals.append("EMA9 > EMA21")
            else:
                bearish += 1
                signals.append("EMA9 < EMA21")

        if ema50 and close > ema50:
            bullish += 1
            signals.append("Above EMA50")
        elif ema50:
            bearish += 1
            signals.append("Below EMA50")

        if vwap and close > vwap:
            bullish += 1
            signals.append("Above VWAP")
        elif vwap:
            bearish += 1
            signals.append("Below VWAP")

        if rsi > 55:
            bullish += 1
        elif rsi < 45:
            bearish += 1

        if bullish > bearish:
            trend = "BULLISH"
            advice = "Market supports BUY calls"
            color = "#00E676"
        elif bearish > bullish:
            trend = "BEARISH"
            advice = "Market favors SHORT/SELL — be cautious with longs"
            color = "#FF1744"
        else:
            trend = "NEUTRAL"
            advice = "Mixed signals — selective stock picking recommended"
            color = "#FFD740"

        return {
            "index": "NIFTY 50",
            "value": round(close, 2),
            "change": change,
            "change_pct": change_pct,
            "trend": trend,
            "advice": advice,
            "color": color,
            "rsi": round(rsi, 1),
            "signals": signals,
        }
    except Exception as e:
        print(f"Nifty trend error: {e}")
        return None


def get_analyst_recommendations(symbol):
    """Get analyst buy/sell/hold ratings from brokerage firms."""
    try:
        ticker = yf.Ticker(symbol)

        # Try recommendations summary first
        rec_summary = None
        try:
            rec_summary = ticker.recommendations
        except Exception:
            pass

        if rec_summary is not None and not rec_summary.empty:
            # Get the most recent recommendations (last 3 months)
            recent = rec_summary.tail(10)
            grades = recent["To Grade"].value_counts() if "To Grade" in recent.columns else pd.Series()

            buy_count = 0
            sell_count = 0
            hold_count = 0
            firms = []

            for _, row in recent.iterrows():
                grade = str(row.get("To Grade", "")).lower()
                firm = str(row.get("Firm", "Unknown"))

                if any(w in grade for w in ["buy", "outperform", "overweight", "accumulate", "add"]):
                    buy_count += 1
                    firms.append({"firm": firm, "rating": "BUY", "grade": row.get("To Grade", "")})
                elif any(w in grade for w in ["sell", "underperform", "underweight", "reduce"]):
                    sell_count += 1
                    firms.append({"firm": firm, "rating": "SELL", "grade": row.get("To Grade", "")})
                else:
                    hold_count += 1
                    firms.append({"firm": firm, "rating": "HOLD", "grade": row.get("To Grade", "")})

            total = buy_count + sell_count + hold_count
            if total == 0:
                return None

            # Consensus score: +1 per buy, -1 per sell, 0 per hold
            consensus_score = (buy_count - sell_count) / total
            if consensus_score > 0.3:
                consensus = "STRONG BUY"
                color = "#00E676"
            elif consensus_score > 0:
                consensus = "BUY"
                color = "#69F0AE"
            elif consensus_score > -0.3:
                consensus = "HOLD"
                color = "#FFD740"
            else:
                consensus = "SELL"
                color = "#FF1744"

            return {
                "consensus": consensus,
                "consensus_score": round(consensus_score, 2),
                "buy": buy_count,
                "hold": hold_count,
                "sell": sell_count,
                "total": total,
                "color": color,
                "firms": firms[:5],  # Top 5 recent
            }
        return None
    except Exception as e:
        print(f"Analyst rec error for {symbol}: {e}")
        return None


def _score_sentiment(text):
    """Score a headline for sentiment. Returns -1 to +1."""
    words = set(re.findall(r'\w+', text.lower()))
    pos = len(words & POSITIVE_WORDS)
    neg = len(words & NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0
    return round((pos - neg) / total, 2)


def get_news_sentiment(symbol):
    """
    Get news sentiment for a stock by checking Google News RSS.
    Returns list of headlines with sentiment scores.
    """
    stock_name = symbol.replace(".NS", "").replace(".BO", "")
    headlines = []

    # Try Google News RSS
    try:
        import urllib.request
        query = f"{stock_name}+stock+India"
        url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read()
        root = ET.fromstring(data)
        for item in root.findall(".//item")[:8]:
            title = item.find("title")
            pub_date = item.find("pubDate")
            if title is not None and title.text:
                text = title.text.strip()
                score = _score_sentiment(text)
                headlines.append({
                    "title": text,
                    "sentiment": score,
                    "sentiment_label": "Positive" if score > 0 else ("Negative" if score < 0 else "Neutral"),
                    "date": pub_date.text.strip() if pub_date is not None and pub_date.text else "",
                })
    except Exception as e:
        print(f"News fetch error for {stock_name}: {e}")

    if not headlines:
        return {"headlines": [], "overall": 0, "label": "No News", "color": "#9E9E9E"}

    avg_sentiment = round(sum(h["sentiment"] for h in headlines) / len(headlines), 2)
    if avg_sentiment > 0.15:
        label = "Bullish News"
        color = "#00E676"
    elif avg_sentiment < -0.15:
        label = "Bearish News"
        color = "#FF1744"
    else:
        label = "Neutral News"
        color = "#FFD740"

    return {
        "headlines": headlines,
        "overall": avg_sentiment,
        "label": label,
        "color": color,
    }


def get_market_pulse():
    """
    Full market context: VIX + Nifty trend + overall market mood.
    Call this once to get the big picture before making any trades.
    """
    vix = get_india_vix()
    nifty = get_nifty_trend()

    # Overall market mood
    mood_score = 0
    if vix:
        if vix["level"] in ("LOW", "VERY_LOW"):
            mood_score += 1
        elif vix["level"] in ("HIGH", "VERY_HIGH"):
            mood_score -= 1

    if nifty:
        if nifty["trend"] == "BULLISH":
            mood_score += 1
        elif nifty["trend"] == "BEARISH":
            mood_score -= 1

    if mood_score >= 1:
        overall = "FAVORABLE"
        overall_text = "Market conditions are favorable for trading"
        overall_color = "#00E676"
    elif mood_score <= -1:
        overall = "CAUTION"
        overall_text = "Market conditions suggest caution — reduce position sizes"
        overall_color = "#FF9100"
    else:
        overall = "NEUTRAL"
        overall_text = "Mixed market signals — be selective with trades"
        overall_color = "#FFD740"

    return {
        "vix": vix,
        "nifty": nifty,
        "overall_mood": overall,
        "overall_text": overall_text,
        "overall_color": overall_color,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }
