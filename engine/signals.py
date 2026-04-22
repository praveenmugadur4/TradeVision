"""
Signal Generation Module — Multi-indicator confluence scoring for buy/sell signals.
"""

import pandas as pd
import numpy as np


# Signal strength constants
STRONG_BUY = "STRONG_BUY"
BUY = "BUY"
HOLD = "HOLD"
SELL = "SELL"
STRONG_SELL = "STRONG_SELL"


def _score_rsi(rsi):
    """Score RSI: oversold = bullish, overbought = bearish."""
    if rsi is None or pd.isna(rsi):
        return 0, "N/A"
    if rsi < 20:
        return 2, "Heavily Oversold — Strong Buy"
    elif rsi < 30:
        return 1, "Oversold — Buy Zone"
    elif rsi < 45:
        return 0.5, "Slightly Bearish"
    elif rsi < 55:
        return 0, "Neutral"
    elif rsi < 70:
        return -0.5, "Slightly Bullish Momentum"
    elif rsi < 80:
        return -1, "Overbought — Sell Zone"
    else:
        return -2, "Heavily Overbought — Strong Sell"


def _score_macd(macd, signal, histogram):
    """Score MACD crossover and histogram direction."""
    if macd is None or signal is None or pd.isna(macd) or pd.isna(signal):
        return 0, "N/A"
    
    score = 0
    reason = ""
    
    if macd > signal:
        score += 1
        reason = "MACD above Signal — Bullish"
        if histogram is not None and not pd.isna(histogram) and histogram > 0:
            score += 0.5
            reason += " (Histogram expanding)"
    else:
        score -= 1
        reason = "MACD below Signal — Bearish"
        if histogram is not None and not pd.isna(histogram) and histogram < 0:
            score -= 0.5
            reason += " (Histogram contracting)"
    
    return score, reason


def _score_bollinger(close, bb_upper, bb_lower, bb_mid):
    """Score Bollinger Band position."""
    if any(v is None or pd.isna(v) for v in [close, bb_upper, bb_lower, bb_mid]):
        return 0, "N/A"
    
    bb_range = bb_upper - bb_lower
    if bb_range == 0:
        return 0, "N/A"
    
    position = (close - bb_lower) / bb_range
    
    if position < 0.05:
        return 2, "Below Lower Band — Strongly Oversold"
    elif position < 0.2:
        return 1, "Near Lower Band — Oversold"
    elif position < 0.4:
        return 0.5, "Below Middle Band"
    elif position < 0.6:
        return 0, "Near Middle Band — Neutral"
    elif position < 0.8:
        return -0.5, "Above Middle Band"
    elif position < 0.95:
        return -1, "Near Upper Band — Overbought"
    else:
        return -2, "Above Upper Band — Strongly Overbought"


def _score_moving_averages(close, ema_9, ema_21, ema_50, sma_200):
    """Score price position relative to moving averages."""
    if close is None or pd.isna(close):
        return 0, "N/A"
    
    score = 0
    reasons = []
    
    if ema_9 is not None and not pd.isna(ema_9):
        if close > ema_9:
            score += 0.5
            reasons.append("Above EMA9")
        else:
            score -= 0.5
            reasons.append("Below EMA9")
    
    if ema_21 is not None and not pd.isna(ema_21):
        if close > ema_21:
            score += 0.5
            reasons.append("Above EMA21")
        else:
            score -= 0.5
            reasons.append("Below EMA21")
    
    if ema_50 is not None and not pd.isna(ema_50):
        if close > ema_50:
            score += 0.5
        else:
            score -= 0.5
    
    if sma_200 is not None and not pd.isna(sma_200):
        if close > sma_200:
            score += 1
            reasons.append("Above SMA200 — Long-term bullish")
        else:
            score -= 1
            reasons.append("Below SMA200 — Long-term bearish")
    
    # EMA crossovers
    if (ema_9 is not None and ema_21 is not None 
            and not pd.isna(ema_9) and not pd.isna(ema_21)):
        if ema_9 > ema_21:
            score += 0.5
            reasons.append("Golden crossover EMA9>EMA21")
        else:
            score -= 0.5
            reasons.append("Death crossover EMA9<EMA21")
    
    return score, " | ".join(reasons) if reasons else "N/A"


def _score_stochastic(k, d):
    """Score Stochastic Oscillator."""
    if k is None or pd.isna(k):
        return 0, "N/A"
    
    if k < 20:
        return 1, "Stoch Oversold"
    elif k < 30 and d is not None and not pd.isna(d) and k > d:
        return 1.5, "Stoch Bullish Crossover in Oversold"
    elif k > 80:
        return -1, "Stoch Overbought"
    elif k > 70 and d is not None and not pd.isna(d) and k < d:
        return -1.5, "Stoch Bearish Crossover in Overbought"
    return 0, "Stoch Neutral"


def _score_adx(adx, di_plus, di_minus):
    """Score ADX trend strength and direction."""
    if adx is None or pd.isna(adx):
        return 0, "N/A"
    
    if adx < 20:
        return 0, "Weak Trend (ADX<20)"
    
    if di_plus is not None and di_minus is not None:
        if not pd.isna(di_plus) and not pd.isna(di_minus):
            if di_plus > di_minus:
                strength = min(adx / 50, 1.5)
                return strength, f"Strong Uptrend (ADX={adx:.0f})"
            else:
                strength = -min(adx / 50, 1.5)
                return strength, f"Strong Downtrend (ADX={adx:.0f})"
    
    return 0, f"Trending (ADX={adx:.0f})"


def _score_supertrend(close, supertrend, direction):
    """Score Supertrend indicator."""
    if supertrend is None or pd.isna(supertrend) or direction is None or pd.isna(direction):
        return 0, "N/A"
    
    if direction == 1 or (close is not None and not pd.isna(close) and close > supertrend):
        return 1, "Supertrend Bullish"
    else:
        return -1, "Supertrend Bearish"


def generate_signals(df):
    """
    Generate buy/sell signals based on multi-indicator confluence.
    
    Returns a dict with:
    - overall_signal: STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    - confidence: 0-100%
    - total_score: raw numerical score
    - breakdown: individual indicator scores and reasons
    - support_resistance: key price levels
    """
    if df is None or df.empty:
        return {"overall_signal": HOLD, "confidence": 0, "breakdown": []}

    latest = df.iloc[-1]
    
    breakdown = []
    total_score = 0
    max_possible = 0

    # RSI
    score, reason = _score_rsi(latest.get("RSI"))
    breakdown.append({"indicator": "RSI", "score": score, "reason": reason, "value": _sv(latest.get("RSI"))})
    total_score += score
    max_possible += 2

    # MACD
    score, reason = _score_macd(latest.get("MACD"), latest.get("MACD_Signal"), latest.get("MACD_Hist"))
    breakdown.append({"indicator": "MACD", "score": score, "reason": reason, "value": _sv(latest.get("MACD"))})
    total_score += score
    max_possible += 1.5

    # Bollinger Bands
    score, reason = _score_bollinger(
        latest.get("Close"), latest.get("BB_Upper"), latest.get("BB_Lower"), latest.get("BB_Mid")
    )
    breakdown.append({"indicator": "Bollinger Bands", "score": score, "reason": reason, "value": _sv(latest.get("Close"))})
    total_score += score
    max_possible += 2

    # Moving Averages
    score, reason = _score_moving_averages(
        latest.get("Close"), latest.get("EMA_9"), latest.get("EMA_21"),
        latest.get("EMA_50"), latest.get("SMA_200")
    )
    breakdown.append({"indicator": "Moving Averages", "score": score, "reason": reason, "value": _sv(latest.get("Close"))})
    total_score += score
    max_possible += 3

    # Stochastic
    score, reason = _score_stochastic(latest.get("STOCH_K"), latest.get("STOCH_D"))
    breakdown.append({"indicator": "Stochastic", "score": score, "reason": reason, "value": _sv(latest.get("STOCH_K"))})
    total_score += score
    max_possible += 1.5

    # ADX
    score, reason = _score_adx(latest.get("ADX"), latest.get("DI_Plus"), latest.get("DI_Minus"))
    breakdown.append({"indicator": "ADX", "score": score, "reason": reason, "value": _sv(latest.get("ADX"))})
    total_score += score
    max_possible += 1.5

    # Supertrend
    score, reason = _score_supertrend(latest.get("Close"), latest.get("Supertrend"), latest.get("Supertrend_Dir"))
    breakdown.append({"indicator": "Supertrend", "score": score, "reason": reason, "value": _sv(latest.get("Supertrend"))})
    total_score += score
    max_possible += 1

    # ─── Determine Overall Signal ───
    if max_possible == 0:
        confidence = 0
    else:
        # Normalize score to -100 to +100 range
        normalized = (total_score / max_possible) * 100

        # Convert to confidence (0-100 where >50 is bullish, <50 is bearish)
        confidence = min(max(50 + normalized / 2, 0), 100)

    if total_score >= 5:
        overall = STRONG_BUY
    elif total_score >= 2:
        overall = BUY
    elif total_score <= -5:
        overall = STRONG_SELL
    elif total_score <= -2:
        overall = SELL
    else:
        overall = HOLD

    # ─── Support & Resistance Levels ───
    support_resistance = _calculate_support_resistance(df)

    return {
        "overall_signal": overall,
        "confidence": round(confidence, 1),
        "total_score": round(total_score, 2),
        "max_score": round(max_possible, 2),
        "breakdown": breakdown,
        "support_resistance": support_resistance,
    }


def _sv(val):
    """Safe value for serialization."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    return round(float(val), 2)


def _calculate_support_resistance(df, lookback=60):
    """Calculate support and resistance levels from recent price action."""
    if df is None or len(df) < lookback:
        lookback = len(df)
    
    recent = df.tail(lookback)
    highs = recent["High"].values
    lows = recent["Low"].values
    close = float(recent["Close"].iloc[-1])
    
    # Simple pivot-based S&R
    pivot = (float(recent["High"].max()) + float(recent["Low"].min()) + close) / 3
    r1 = 2 * pivot - float(recent["Low"].min())
    r2 = pivot + (float(recent["High"].max()) - float(recent["Low"].min()))
    s1 = 2 * pivot - float(recent["High"].max())
    s2 = pivot - (float(recent["High"].max()) - float(recent["Low"].min()))

    return {
        "pivot": round(pivot, 2),
        "resistance_1": round(r1, 2),
        "resistance_2": round(r2, 2),
        "support_1": round(s1, 2),
        "support_2": round(s2, 2),
        "52w_high": round(float(df["High"].tail(252).max()), 2) if len(df) > 0 else None,
        "52w_low": round(float(df["Low"].tail(252).min()), 2) if len(df) > 0 else None,
    }


def generate_historical_signals(df):
    """
    Generate signals for every row in the DataFrame (used for backtesting).
    
    Returns DataFrame with 'Signal' column: 1 (BUY), -1 (SELL), 0 (HOLD)
    """
    if df is None or df.empty:
        return df

    result = df.copy()
    result["Signal"] = 0
    result["Signal_Score"] = 0.0

    for i in range(30, len(result)):  # Need at least 30 bars for indicators
        row = result.iloc[i]
        score = 0

        # RSI
        rsi = row.get("RSI")
        if rsi is not None and not pd.isna(rsi):
            if rsi < 30:
                score += 1.5
            elif rsi < 40:
                score += 0.5
            elif rsi > 70:
                score -= 1.5
            elif rsi > 60:
                score -= 0.5

        # MACD
        macd = row.get("MACD")
        macd_sig = row.get("MACD_Signal")
        if macd is not None and macd_sig is not None and not pd.isna(macd) and not pd.isna(macd_sig):
            if macd > macd_sig:
                score += 1
            else:
                score -= 1

        # EMA crossover
        ema9 = row.get("EMA_9")
        ema21 = row.get("EMA_21")
        if ema9 is not None and ema21 is not None and not pd.isna(ema9) and not pd.isna(ema21):
            if ema9 > ema21:
                score += 1
            else:
                score -= 1

        # Bollinger Band position
        close = row.get("Close")
        bb_lower = row.get("BB_Lower")
        bb_upper = row.get("BB_Upper")
        if all(v is not None and not pd.isna(v) for v in [close, bb_lower, bb_upper]):
            bb_range = bb_upper - bb_lower
            if bb_range > 0:
                pct = (close - bb_lower) / bb_range
                if pct < 0.1:
                    score += 1.5
                elif pct > 0.9:
                    score -= 1.5

        # Supertrend
        st_dir = row.get("Supertrend_Dir")
        if st_dir is not None and not pd.isna(st_dir):
            if st_dir == 1:
                score += 1
            else:
                score -= 1

        result.iloc[i, result.columns.get_loc("Signal_Score")] = score
        
        if score >= 2.5:
            result.iloc[i, result.columns.get_loc("Signal")] = 1  # BUY
        elif score <= -2.5:
            result.iloc[i, result.columns.get_loc("Signal")] = -1  # SELL

    return result
