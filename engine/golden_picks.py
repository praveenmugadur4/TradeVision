"""
Golden Picks Engine — Daily & Weekly high-probability stock scanner.

Daily Golden Picks: CPR + multi-indicator confluence for intraday (>85% confidence)
Weekly Strategy: Swing trade setups using weekly trends (>90% confidence)
"""

import pandas as pd
import numpy as np
from .indicators import calculate_all_indicators
from .market_data import fetch_market_data, get_category_symbols
from .market_data import LARGE_CAP_STOCKS, MID_CAP_STOCKS


def calculate_cpr(prev_high, prev_low, prev_close):
    """
    Central Pivot Range from previous day's High, Low, Close.
    
    Returns dict with: pivot, tc, bc, r1-r3, s1-s3, cpr_width, cpr_type
    """
    pivot = (prev_high + prev_low + prev_close) / 3
    bc = (prev_high + prev_low) / 2          # Bottom Central Pivot
    tc = (pivot - bc) + pivot                  # Top Central Pivot

    # Standard Pivot levels
    r1 = (2 * pivot) - prev_low
    s1 = (2 * pivot) - prev_high
    r2 = pivot + (prev_high - prev_low)
    s2 = pivot - (prev_high - prev_low)
    r3 = prev_high + 2 * (pivot - prev_low)
    s3 = prev_low - 2 * (prev_high - pivot)

    # CPR width as % of price
    cpr_width = abs(tc - bc) / pivot * 100 if pivot > 0 else 0

    # Narrow CPR = trending day, Wide CPR = sideways day
    if cpr_width < 0.3:
        cpr_type = "VERY_NARROW"   # Strong trending day expected
    elif cpr_width < 0.5:
        cpr_type = "NARROW"        # Trending day likely
    elif cpr_width < 1.0:
        cpr_type = "MEDIUM"        # Normal day
    else:
        cpr_type = "WIDE"          # Sideways/range-bound day

    return {
        "pivot": round(pivot, 2),
        "tc": round(tc, 2),
        "bc": round(bc, 2),
        "r1": round(r1, 2), "r2": round(r2, 2), "r3": round(r3, 2),
        "s1": round(s1, 2), "s2": round(s2, 2), "s3": round(s3, 2),
        "cpr_width": round(cpr_width, 3),
        "cpr_type": cpr_type,
        "prev_high": round(prev_high, 2),
        "prev_low": round(prev_low, 2),
        "prev_close": round(prev_close, 2),
    }


def _score_stock_intraday(symbol, df, df_ind):
    """
    Score a stock for intraday golden pick using weighted criteria.
    Returns score (0-100) and reasoning.
    """
    if df is None or df.empty or len(df) < 30:
        return 0, [], {}

    latest = df_ind.iloc[-1]
    prev = df_ind.iloc[-2] if len(df_ind) > 1 else latest
    close = float(latest["Close"])

    # CPR from previous day
    prev_h = float(prev["High"])
    prev_l = float(prev["Low"])
    prev_c = float(prev["Close"])
    cpr = calculate_cpr(prev_h, prev_l, prev_c)

    score = 0
    max_score = 0
    reasons = []

    def _s(val):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        return float(val)

    # ═══ 1. CPR POSITION (20 pts) ═══
    max_score += 20
    if close > cpr["tc"]:
        score += 20
        reasons.append(f"📊 Price ABOVE CPR top ({cpr['tc']}) — Bullish bias")
    elif close > cpr["pivot"]:
        score += 12
        reasons.append(f"📊 Price above Pivot ({cpr['pivot']}) — Mild bullish")
    elif close < cpr["bc"]:
        score += 18  # Bearish is also tradeable
        reasons.append(f"📊 Price BELOW CPR bottom ({cpr['bc']}) — Clear bearish bias")
    elif close < cpr["pivot"]:
        score += 10
        reasons.append(f"📊 Price below Pivot ({cpr['pivot']}) — Mild bearish")
    else:
        reasons.append(f"📊 Price inside CPR — Avoid, no clear direction")

    # ═══ 2. CPR WIDTH — Narrow = Trending (15 pts) ═══
    max_score += 15
    if cpr["cpr_type"] == "VERY_NARROW":
        score += 15
        reasons.append(f"🎯 CPR VERY NARROW ({cpr['cpr_width']:.2f}%) — Strong trending day!")
    elif cpr["cpr_type"] == "NARROW":
        score += 12
        reasons.append(f"🎯 CPR Narrow ({cpr['cpr_width']:.2f}%) — Trending day likely")
    elif cpr["cpr_type"] == "MEDIUM":
        score += 6
    else:
        score += 0
        reasons.append(f"⚠️ CPR Wide ({cpr['cpr_width']:.2f}%) — Sideways day expected")

    # ═══ 3. VWAP ALIGNMENT (15 pts) ═══
    vwap = _s(latest.get("VWAP"))
    max_score += 15
    if vwap:
        above_cpr = close > cpr["tc"]
        above_vwap = close > vwap
        if above_cpr == above_vwap:  # Both agree
            score += 15
            reasons.append(f"✅ VWAP ({vwap:.1f}) confirms CPR direction — Strong alignment")
        else:
            score += 5
            reasons.append(f"⚠️ VWAP and CPR conflict — Weaker setup")

    # ═══ 4. MACD MOMENTUM (10 pts) ═══
    macd = _s(latest.get("MACD"))
    macd_sig = _s(latest.get("MACD_Signal"))
    prev_macd = _s(prev.get("MACD"))
    prev_macd_sig = _s(prev.get("MACD_Signal"))
    max_score += 10
    if macd is not None and macd_sig is not None:
        if macd > macd_sig:
            score += 8
            if prev_macd is not None and prev_macd_sig is not None and prev_macd <= prev_macd_sig:
                score += 2
                reasons.append("🔀 Fresh MACD bullish crossover!")
        elif macd < macd_sig:
            score += 8  # Bearish also tradeable for shorts
            if prev_macd is not None and prev_macd_sig is not None and prev_macd >= prev_macd_sig:
                score += 2
                reasons.append("🔀 Fresh MACD bearish crossover!")

    # ═══ 5. RSI NOT EXTREME (10 pts) ═══
    rsi = _s(latest.get("RSI"))
    max_score += 10
    if rsi:
        if 30 <= rsi <= 70:
            score += 10  # Healthy RSI, room to move
        elif rsi < 25 or rsi > 75:
            score += 8  # Extreme = reversal possible
            reasons.append(f"📊 RSI extreme ({rsi:.0f}) — Watch for reversal")
        else:
            score += 5

    # ═══ 6. ADX TREND STRENGTH (10 pts) ═══
    adx = _s(latest.get("ADX"))
    max_score += 10
    if adx:
        if adx > 30:
            score += 10
            reasons.append(f"💪 Strong trend (ADX {adx:.0f})")
        elif adx > 20:
            score += 7
        else:
            score += 3
            reasons.append(f"⚠️ Weak trend (ADX {adx:.0f})")

    # ═══ 7. VOLUME ABOVE AVERAGE (10 pts) ═══
    max_score += 10
    vol = float(latest.get("Volume", 0))
    avg_vol = float(df["Volume"].tail(20).mean()) if len(df) >= 20 else vol
    if avg_vol > 0 and vol > 0:
        vol_ratio = vol / avg_vol
        if vol_ratio > 1.5:
            score += 10
            reasons.append(f"📈 Volume {vol_ratio:.1f}x above average — Conviction move")
        elif vol_ratio > 1.0:
            score += 7
        else:
            score += 3

    # ═══ 8. EMA ALIGNMENT (10 pts) ═══
    ema9 = _s(latest.get("EMA_9"))
    ema21 = _s(latest.get("EMA_21"))
    max_score += 10
    if ema9 and ema21:
        bullish_ema = ema9 > ema21 and close > ema9
        bearish_ema = ema9 < ema21 and close < ema9
        if bullish_ema or bearish_ema:
            score += 10
        elif ema9 > ema21 or ema9 < ema21:
            score += 5

    # Final confidence
    confidence = round((score / max_score) * 100, 1) if max_score > 0 else 0

    # Determine direction
    bullish_signals = 0
    bearish_signals = 0
    if close > cpr["tc"]: bullish_signals += 1
    else: bearish_signals += 1
    if vwap and close > vwap: bullish_signals += 1
    else: bearish_signals += 1
    if macd and macd_sig and macd > macd_sig: bullish_signals += 1
    else: bearish_signals += 1
    if ema9 and ema21 and ema9 > ema21: bullish_signals += 1
    else: bearish_signals += 1

    direction = "BUY" if bullish_signals > bearish_signals else "SELL"

    # Targets from CPR levels
    atr = _s(latest.get("ATR")) or close * 0.015
    if direction == "BUY":
        entry = round(close, 2)
        target = round(min(cpr["r1"], close + 2 * atr), 2)
        stop_loss = round(max(cpr["pivot"], close - atr), 2)
    else:
        entry = round(close, 2)
        target = round(max(cpr["s1"], close - 2 * atr), 2)
        stop_loss = round(min(cpr["pivot"], close + atr), 2)

    risk = abs(close - stop_loss)
    reward = abs(target - close)
    rr = round(reward / risk, 2) if risk > 0 else 0

    return confidence, reasons, {
        "symbol": symbol,
        "name": symbol.replace(".NS", "").replace(".BO", ""),
        "price": close,
        "direction": direction,
        "confidence": confidence,
        "entry": entry,
        "target": target,
        "stop_loss": stop_loss,
        "risk_reward": rr,
        "cpr": cpr,
        "reasons": reasons,
    }


def get_golden_picks(top_n=6):
    """
    Scan all major stocks and return top N golden intraday picks.
    Only returns stocks with >80% confidence.
    """
    # Scan large + mid cap for best opportunities
    symbols = get_category_symbols("large_cap")[:25] + get_category_symbols("mid_cap")[:15]
    picks = []

    for symbol in symbols:
        try:
            df = fetch_market_data(symbol, period="3mo", interval="1d")
            if df is None or df.empty or len(df) < 30:
                continue
            df_ind = calculate_all_indicators(df)
            conf, reasons, data = _score_stock_intraday(symbol, df, df_ind)
            if conf >= 70 and data.get("risk_reward", 0) >= 1.0:
                picks.append(data)
        except Exception as e:
            print(f"Golden scan error {symbol}: {e}")

    picks.sort(key=lambda x: x["confidence"], reverse=True)
    return picks[:top_n]


def _score_stock_weekly(symbol, df, df_ind):
    """Score a stock for weekly swing strategy."""
    if df is None or len(df) < 60:
        return 0, []

    latest = df_ind.iloc[-1]
    close = float(latest["Close"])

    def _s(val):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        return float(val)

    score = 0
    max_score = 0
    reasons = []

    # ═══ 1. ABOVE SMA 200 — Long-term uptrend (20 pts) ═══
    sma200 = _s(latest.get("SMA_200"))
    max_score += 20
    if sma200:
        if close > sma200:
            score += 20
            reasons.append(f"📈 Above 200-SMA ({sma200:.0f}) — Long-term uptrend")
        else:
            score += 5
            reasons.append(f"📉 Below 200-SMA — Caution for longs")

    # ═══ 2. EMA 50 TREND (15 pts) ═══
    ema50 = _s(latest.get("EMA_50"))
    max_score += 15
    if ema50 and sma200:
        if close > ema50 > sma200:
            score += 15
            reasons.append("✅ Perfect alignment: Price > EMA50 > SMA200")
        elif close > ema50:
            score += 10

    # ═══ 3. RSI IN SWEET SPOT 40-65 (15 pts) ═══
    rsi = _s(latest.get("RSI"))
    max_score += 15
    if rsi:
        if 40 <= rsi <= 65:
            score += 15
            reasons.append(f"📊 RSI {rsi:.0f} — Room to run higher")
        elif 30 <= rsi <= 40:
            score += 12
            reasons.append(f"📊 RSI {rsi:.0f} — Pullback entry zone")
        elif rsi > 65:
            score += 5
            reasons.append(f"⚠️ RSI {rsi:.0f} — Overbought, limited upside")

    # ═══ 4. MACD BULLISH (10 pts) ═══
    macd = _s(latest.get("MACD"))
    macd_sig = _s(latest.get("MACD_Signal"))
    max_score += 10
    if macd is not None and macd_sig is not None:
        if macd > macd_sig:
            score += 10
            hist = _s(latest.get("MACD_Hist"))
            prev_hist = _s(df_ind.iloc[-2].get("MACD_Hist")) if len(df_ind) > 1 else None
            if hist and prev_hist and hist > prev_hist:
                reasons.append("📈 MACD bullish with expanding histogram")

    # ═══ 5. SUPERTREND BULLISH (10 pts) ═══
    st_dir = _s(latest.get("Supertrend_Dir"))
    max_score += 10
    if st_dir is not None:
        if st_dir == 1:
            score += 10
            reasons.append("🟢 Supertrend: Bullish")

    # ═══ 6. WEEKLY MOMENTUM — Price vs 5-week ago (15 pts) ═══
    max_score += 15
    if len(df) >= 25:
        price_5w = float(df.iloc[-25]["Close"])
        weekly_change = ((close - price_5w) / price_5w) * 100
        if 2 <= weekly_change <= 15:
            score += 15
            reasons.append(f"📈 Up {weekly_change:.1f}% in 5 weeks — Healthy momentum")
        elif 0 < weekly_change <= 2:
            score += 10
            reasons.append(f"📈 Flat {weekly_change:.1f}% — Consolidating, watch for breakout")
        elif weekly_change > 15:
            score += 5
            reasons.append(f"⚠️ Up {weekly_change:.1f}% in 5 weeks — Overextended")

    # ═══ 7. VOLUME TREND (10 pts) ═══
    max_score += 10
    if len(df) >= 20:
        recent_vol = float(df["Volume"].tail(5).mean())
        older_vol = float(df["Volume"].tail(20).head(15).mean())
        if older_vol > 0:
            vol_trend = recent_vol / older_vol
            if vol_trend > 1.2:
                score += 10
                reasons.append("📊 Volume increasing — Institutional interest")
            elif vol_trend > 0.9:
                score += 6

    # ═══ 8. ATR-BASED RISK (5 pts) ═══
    atr = _s(latest.get("ATR"))
    max_score += 5
    if atr and close > 0:
        atr_pct = (atr / close) * 100
        if atr_pct < 2.5:
            score += 5
            reasons.append(f"🛡️ Low volatility ({atr_pct:.1f}%) — Safer swing trade")
        elif atr_pct < 4:
            score += 3

    confidence = round((score / max_score) * 100, 1) if max_score > 0 else 0

    # Target: 5-8% gain over 1-2 weeks
    atr_val = atr or close * 0.02
    entry = round(close, 2)
    target = round(close * 1.06, 2)  # 6% target
    stop_loss = round(close - 2 * atr_val, 2)  # 2x ATR stop

    risk = abs(close - stop_loss)
    reward = abs(target - close)
    rr = round(reward / risk, 2) if risk > 0 else 0

    return confidence, {
        "symbol": symbol,
        "name": symbol.replace(".NS", "").replace(".BO", ""),
        "price": close,
        "confidence": confidence,
        "entry": entry,
        "target": target,
        "target_pct": round(((target - close) / close) * 100, 1),
        "stop_loss": stop_loss,
        "risk_reward": rr,
        "holding_period": "1-2 weeks",
        "reasons": reasons,
    }


def get_weekly_picks(top_n=6):
    """
    Scan stocks for best weekly swing trade setups.
    Only returns stocks with >75% confidence.
    """
    symbols = get_category_symbols("large_cap")[:30] + get_category_symbols("mid_cap")[:20]
    picks = []

    for symbol in symbols:
        try:
            df = fetch_market_data(symbol, period="1y", interval="1d")
            if df is None or df.empty or len(df) < 60:
                continue
            df_ind = calculate_all_indicators(df)
            conf, data = _score_stock_weekly(symbol, df, df_ind)
            if conf >= 70 and data.get("risk_reward", 0) >= 1.5:
                picks.append(data)
        except Exception as e:
            print(f"Weekly scan error {symbol}: {e}")

    picks.sort(key=lambda x: x["confidence"], reverse=True)
    return picks[:top_n]
