"""
Intraday Tips Engine v2 — Enhanced with VWAP, Volume Confirmation,
Multi-Timeframe Analysis, Smart S/R Targets, and Weighted Scoring.
"""

import pandas as pd
import numpy as np
from .indicators import calculate_all_indicators, calculate_fibonacci_levels
from .signals import generate_signals


def _safe(val):
    """Return float or None if NaN."""
    if val is None or (isinstance(val, float) and (pd.isna(val) or np.isinf(val))):
        return None
    return float(val)


def _pct(a, b):
    """Percentage difference."""
    if b and b != 0:
        return round(((a - b) / b) * 100, 2)
    return 0


def _find_support_resistance(df, lookback=60):
    """Find key support/resistance levels from recent price action."""
    recent = df.tail(min(lookback, len(df)))
    highs = recent["High"].values
    lows = recent["Low"].values
    close = float(recent["Close"].iloc[-1])

    # Pivot-based levels
    h = float(recent["High"].max())
    l = float(recent["Low"].min())
    pivot = (h + l + close) / 3

    r1 = 2 * pivot - l
    r2 = pivot + (h - l)
    s1 = 2 * pivot - h
    s2 = pivot - (h - l)

    # Find nearest support below price and resistance above
    levels_above = sorted([v for v in [r1, r2, h] if v > close])
    levels_below = sorted([v for v in [s1, s2, l] if v < close], reverse=True)

    return {
        "pivot": round(pivot, 2),
        "nearest_resistance": round(levels_above[0], 2) if levels_above else round(close * 1.03, 2),
        "nearest_support": round(levels_below[0], 2) if levels_below else round(close * 0.97, 2),
        "r1": round(r1, 2), "r2": round(r2, 2),
        "s1": round(s1, 2), "s2": round(s2, 2),
    }


def generate_intraday_tips(symbol, df):
    """
    Generate actionable intraday tips using weighted multi-indicator scoring.

    Improvements over v1:
    - VWAP analysis (most important intraday indicator)
    - Volume confirmation via MFI, CMF, OBV trend
    - Smart targets using S/R + Fibonacci instead of raw ATR
    - Stochastic crossover detection
    - Weighted scoring (not all indicators equal)
    - Multi-timeframe trend context
    """
    if df is None or df.empty or len(df) < 30:
        return {"action": "WAIT", "symbol": symbol, "reasoning": ["Insufficient data"], "confidence": 0, "tips": []}

    df_ind = calculate_all_indicators(df)
    latest = df_ind.iloc[-1]
    prev = df_ind.iloc[-2] if len(df_ind) > 1 else latest
    prev2 = df_ind.iloc[-3] if len(df_ind) > 2 else prev

    close = float(latest.get("Close", 0))
    high = float(latest.get("High", 0))
    low = float(latest.get("Low", 0))
    volume = float(latest.get("Volume", 0))
    atr = _safe(latest.get("ATR")) or close * 0.02

    signals = generate_signals(df_ind)
    fib = calculate_fibonacci_levels(df_ind)
    sr = _find_support_resistance(df_ind)

    # Weighted scoring system: each indicator contributes a weighted score
    # Positive = bullish, Negative = bearish
    score = 0.0
    max_score = 0.0
    reasoning = []

    # ══════════════════════════════════════════════════════════════
    # 1. VWAP ANALYSIS (Weight: 2.0) — King of intraday indicators
    # ══════════════════════════════════════════════════════════════
    vwap = _safe(latest.get("VWAP"))
    weight_vwap = 2.0
    max_score += weight_vwap
    if vwap and close:
        vwap_dist = _pct(close, vwap)
        if close > vwap:
            score += weight_vwap
            if vwap_dist > 1.5:
                reasoning.append(f"🔵 VWAP: Price ₹{close:.1f} is {vwap_dist:.1f}% ABOVE VWAP ₹{vwap:.1f} — Strong institutional buying")
            else:
                reasoning.append(f"🔵 VWAP: Price above VWAP ₹{vwap:.1f} — Buyers in control")
        else:
            score -= weight_vwap
            if vwap_dist < -1.5:
                reasoning.append(f"🔴 VWAP: Price ₹{close:.1f} is {abs(vwap_dist):.1f}% BELOW VWAP ₹{vwap:.1f} — Strong selling pressure")
            else:
                reasoning.append(f"🔴 VWAP: Price below VWAP ₹{vwap:.1f} — Sellers in control")

    # ══════════════════════════════════════════════════════════════
    # 2. RSI (Weight: 1.5) — Momentum oscillator
    # ══════════════════════════════════════════════════════════════
    rsi = _safe(latest.get("RSI"))
    prev_rsi = _safe(prev.get("RSI"))
    weight_rsi = 1.5
    max_score += weight_rsi
    if rsi:
        if rsi < 25:
            score += weight_rsi
            reasoning.append(f"📊 RSI {rsi:.1f} — Deeply oversold, high probability reversal UP")
        elif rsi < 35:
            score += weight_rsi * 0.7
            reasoning.append(f"📊 RSI {rsi:.1f} — Oversold zone, watching for bounce")
        elif rsi > 75:
            score -= weight_rsi
            reasoning.append(f"📊 RSI {rsi:.1f} — Deeply overbought, high probability pullback")
        elif rsi > 65:
            score -= weight_rsi * 0.7
            reasoning.append(f"📊 RSI {rsi:.1f} — Overbought zone, caution")
        else:
            reasoning.append(f"📊 RSI {rsi:.1f} — Neutral zone")
        # RSI momentum direction
        if prev_rsi and rsi > prev_rsi and rsi < 60:
            score += 0.3
        elif prev_rsi and rsi < prev_rsi and rsi > 40:
            score -= 0.3

    # ══════════════════════════════════════════════════════════════
    # 3. MACD CROSSOVER (Weight: 1.5) — Trend momentum
    # ══════════════════════════════════════════════════════════════
    macd = _safe(latest.get("MACD"))
    macd_sig = _safe(latest.get("MACD_Signal"))
    macd_hist = _safe(latest.get("MACD_Hist"))
    prev_macd = _safe(prev.get("MACD"))
    prev_macd_sig = _safe(prev.get("MACD_Signal"))
    weight_macd = 1.5
    max_score += weight_macd
    if macd is not None and macd_sig is not None:
        if macd > macd_sig:
            score += weight_macd
            # Fresh crossover = extra weight
            if prev_macd is not None and prev_macd_sig is not None and prev_macd <= prev_macd_sig:
                score += 0.5
                reasoning.append("🔀 MACD: FRESH bullish crossover — Strong buy signal!")
            else:
                reasoning.append("📈 MACD above signal — Bullish momentum continuing")
        else:
            score -= weight_macd
            if prev_macd is not None and prev_macd_sig is not None and prev_macd >= prev_macd_sig:
                score -= 0.5
                reasoning.append("🔀 MACD: FRESH bearish crossover — Strong sell signal!")
            else:
                reasoning.append("📉 MACD below signal — Bearish momentum")
        # Histogram expanding?
        if macd_hist is not None:
            prev_hist = _safe(prev.get("MACD_Hist"))
            if prev_hist is not None:
                if macd_hist > 0 and macd_hist > prev_hist:
                    score += 0.3
                elif macd_hist < 0 and macd_hist < prev_hist:
                    score -= 0.3

    # ══════════════════════════════════════════════════════════════
    # 4. EMA TREND (Weight: 1.5) — Short-term direction
    # ══════════════════════════════════════════════════════════════
    ema9 = _safe(latest.get("EMA_9"))
    ema21 = _safe(latest.get("EMA_21"))
    ema50 = _safe(latest.get("EMA_50"))
    weight_ema = 1.5
    max_score += weight_ema
    if ema9 and ema21:
        if ema9 > ema21:
            score += weight_ema * 0.7
            if close > ema9:
                score += weight_ema * 0.3
                reasoning.append(f"📈 Trend UP: Price > EMA9 > EMA21 — Strong uptrend")
            else:
                reasoning.append(f"📈 EMA9 > EMA21 — Uptrend, but price pulling back to EMA")
        else:
            score -= weight_ema * 0.7
            if close < ema9:
                score -= weight_ema * 0.3
                reasoning.append(f"📉 Trend DOWN: Price < EMA9 < EMA21 — Strong downtrend")
            else:
                reasoning.append(f"📉 EMA9 < EMA21 — Downtrend, price bouncing")

    # ══════════════════════════════════════════════════════════════
    # 5. VOLUME CONFIRMATION (Weight: 1.5) — MFI + CMF + OBV
    # ══════════════════════════════════════════════════════════════
    mfi = _safe(latest.get("MFI"))
    cmf = _safe(latest.get("CMF"))
    obv = _safe(latest.get("OBV"))
    prev_obv = _safe(prev.get("OBV"))
    weight_vol = 1.5
    max_score += weight_vol
    vol_bull = 0
    vol_bear = 0
    vol_reasons = []

    if mfi is not None:
        if mfi < 20:
            vol_bull += 1
            vol_reasons.append(f"MFI {mfi:.0f} oversold")
        elif mfi > 80:
            vol_bear += 1
            vol_reasons.append(f"MFI {mfi:.0f} overbought")
        elif mfi > 50:
            vol_bull += 0.5
        else:
            vol_bear += 0.5

    if cmf is not None:
        if cmf > 0.05:
            vol_bull += 1
            vol_reasons.append(f"CMF +{cmf:.2f} money flowing in")
        elif cmf < -0.05:
            vol_bear += 1
            vol_reasons.append(f"CMF {cmf:.2f} money flowing out")

    if obv is not None and prev_obv is not None:
        if obv > prev_obv:
            vol_bull += 0.5
        else:
            vol_bear += 0.5

    if vol_bull > vol_bear:
        score += weight_vol * min(vol_bull / 2, 1)
        reasoning.append(f"💰 Volume CONFIRMS buying: {', '.join(vol_reasons)}" if vol_reasons else "💰 Volume supports upside")
    elif vol_bear > vol_bull:
        score -= weight_vol * min(vol_bear / 2, 1)
        reasoning.append(f"💰 Volume CONFIRMS selling: {', '.join(vol_reasons)}" if vol_reasons else "💰 Volume supports downside")

    # ══════════════════════════════════════════════════════════════
    # 6. BOLLINGER BANDS (Weight: 1.0) — Mean reversion
    # ══════════════════════════════════════════════════════════════
    bb_upper = _safe(latest.get("BB_Upper"))
    bb_lower = _safe(latest.get("BB_Lower"))
    bb_mid = _safe(latest.get("BB_Mid"))
    weight_bb = 1.0
    max_score += weight_bb
    if bb_upper and bb_lower and close:
        bb_range = bb_upper - bb_lower
        if bb_range > 0:
            pct = (close - bb_lower) / bb_range
            if pct < 0.1:
                score += weight_bb
                reasoning.append(f"📊 Bollinger: Price at LOWER band — Mean reversion BUY zone")
            elif pct < 0.25:
                score += weight_bb * 0.5
            elif pct > 0.9:
                score -= weight_bb
                reasoning.append(f"📊 Bollinger: Price at UPPER band — Overbought, potential pullback")
            elif pct > 0.75:
                score -= weight_bb * 0.5

    # ══════════════════════════════════════════════════════════════
    # 7. SUPERTREND (Weight: 1.0) — Trend following
    # ══════════════════════════════════════════════════════════════
    st_dir = _safe(latest.get("Supertrend_Dir"))
    weight_st = 1.0
    max_score += weight_st
    if st_dir is not None:
        if st_dir == 1:
            score += weight_st
            reasoning.append("🟢 Supertrend: BULLISH — Trend supports buying")
        else:
            score -= weight_st
            reasoning.append("🔴 Supertrend: BEARISH — Trend supports selling")

    # ══════════════════════════════════════════════════════════════
    # 8. STOCHASTIC (Weight: 1.0) — Overbought/Oversold
    # ══════════════════════════════════════════════════════════════
    stoch_k = _safe(latest.get("STOCH_K"))
    stoch_d = _safe(latest.get("STOCH_D"))
    weight_stoch = 1.0
    max_score += weight_stoch
    if stoch_k is not None:
        if stoch_k < 20:
            score += weight_stoch
            if stoch_d and stoch_k > stoch_d:
                score += 0.3
                reasoning.append(f"📊 Stochastic {stoch_k:.0f} — Oversold with bullish crossover!")
            else:
                reasoning.append(f"📊 Stochastic {stoch_k:.0f} — Oversold")
        elif stoch_k > 80:
            score -= weight_stoch
            if stoch_d and stoch_k < stoch_d:
                score -= 0.3
                reasoning.append(f"📊 Stochastic {stoch_k:.0f} — Overbought with bearish crossover!")
            else:
                reasoning.append(f"📊 Stochastic {stoch_k:.0f} — Overbought")

    # ══════════════════════════════════════════════════════════════
    # 9. WILLIAMS %R + CCI (Weight: 0.5 each) — Confirmation
    # ══════════════════════════════════════════════════════════════
    willr = _safe(latest.get("WILLR"))
    cci = _safe(latest.get("CCI"))
    if willr is not None:
        max_score += 0.5
        if willr < -80:
            score += 0.5
        elif willr > -20:
            score -= 0.5
    if cci is not None:
        max_score += 0.5
        if cci < -100:
            score += 0.5
        elif cci > 100:
            score -= 0.5

    # ══════════════════════════════════════════════════════════════
    # 10. ADX TREND STRENGTH (Modifier) — Amplifies or dampens
    # ══════════════════════════════════════════════════════════════
    adx = _safe(latest.get("ADX"))
    di_plus = _safe(latest.get("DI_Plus"))
    di_minus = _safe(latest.get("DI_Minus"))
    if adx:
        if adx > 30:
            reasoning.append(f"💪 ADX {adx:.0f} — STRONG trend, signals are reliable")
            score *= 1.15  # Amplify in strong trends
        elif adx > 20:
            reasoning.append(f"📊 ADX {adx:.0f} — Moderate trend")
        else:
            reasoning.append(f"⚠️ ADX {adx:.0f} — WEAK trend, signals less reliable")
            score *= 0.85  # Dampen in weak trends

    # ═══════════════════════════════════════════
    # DECISION ENGINE
    # ═══════════════════════════════════════════
    score_pct = (score / max_score * 100) if max_score > 0 else 0

    if score_pct >= 45:
        action = "BUY"
        confidence = min(int(50 + score_pct * 0.5), 95)
    elif score_pct <= -45:
        action = "SELL"
        confidence = min(int(50 + abs(score_pct) * 0.5), 95)
    elif score_pct >= 25:
        action = "BUY"
        confidence = min(int(40 + score_pct * 0.4), 70)
    elif score_pct <= -25:
        action = "SELL"
        confidence = min(int(40 + abs(score_pct) * 0.4), 70)
    else:
        action = "WAIT"
        confidence = max(30, 50 - int(abs(score_pct)))

    # ═══════════════════════════════════════════
    # SMART TARGET CALCULATION (S/R + Fib + ATR)
    # ═══════════════════════════════════════════
    entry_price = round(close, 2)

    if action == "BUY":
        # Target: nearest resistance, capped at 2x ATR
        raw_target = sr["nearest_resistance"]
        atr_target = close + 2 * atr
        fib_target = fib.get("fib_382", atr_target) if fib.get("fib_382", 0) > close else atr_target
        target = round(min(raw_target, atr_target, max(fib_target, close + atr)), 2)
        # SL: nearest support, minimum 1x ATR
        raw_sl = sr["nearest_support"]
        atr_sl = close - atr
        stop_loss = round(max(raw_sl, atr_sl), 2)
    elif action == "SELL":
        raw_target = sr["nearest_support"]
        atr_target = close - 2 * atr
        fib_target = fib.get("fib_618", atr_target) if fib.get("fib_618", 0) < close else atr_target
        target = round(max(raw_target, atr_target, min(fib_target, close - atr)), 2)
        raw_sl = sr["nearest_resistance"]
        atr_sl = close + atr
        stop_loss = round(min(raw_sl, atr_sl), 2)
    else:
        target = entry_price
        stop_loss = entry_price

    # Risk:Reward
    risk = abs(close - stop_loss)
    reward = abs(target - close)
    risk_reward = round(reward / risk, 2) if risk > 0 else 0

    # If R:R is terrible, downgrade to WAIT
    if action != "WAIT" and risk_reward < 1.0:
        reasoning.append(f"⚠️ Risk:Reward {risk_reward} is below 1.0 — Downgraded to WAIT")
        action = "WAIT"
        confidence = max(confidence - 20, 30)

    # ═══════════════════════════════════════════
    # ACTIONABLE TIPS
    # ═══════════════════════════════════════════
    tips = []
    if action == "BUY":
        tips.append(f"💰 Entry: ₹{entry_price} | Target: ₹{target} (+{_pct(target, entry_price):.1f}%)")
        tips.append(f"🛡️ Stop Loss: ₹{stop_loss} ({_pct(stop_loss, entry_price):.1f}%)")
        tips.append(f"📐 Risk:Reward = 1:{risk_reward}")
        if vwap and close > vwap:
            tips.append(f"✅ Trading above VWAP — Institutional support")
        if risk_reward >= 2:
            tips.append("🌟 Excellent R:R ratio — High probability setup")
    elif action == "SELL":
        tips.append(f"💰 Short/Exit: ₹{entry_price} | Target: ₹{target} ({_pct(target, entry_price):.1f}%)")
        tips.append(f"🛡️ Stop Loss: ₹{stop_loss} (+{_pct(stop_loss, entry_price):.1f}%)")
        tips.append(f"📐 Risk:Reward = 1:{risk_reward}")
        if vwap and close < vwap:
            tips.append(f"✅ Trading below VWAP — Institutions selling")
    else:
        tips.append("⏳ No clear setup — Avoid trading this stock now")
        tips.append("👀 Wait for VWAP crossover or MACD crossover for entry")
        if adx and adx < 20:
            tips.append("📊 Market is ranging — Look for breakout above/below Bollinger Bands")

    return {
        "symbol": symbol,
        "action": action,
        "confidence": confidence,
        "entry_price": entry_price,
        "target": target,
        "stop_loss": stop_loss,
        "risk_reward": risk_reward,
        "current_price": close,
        "reasoning": reasoning,
        "tips": tips,
        "signal_data": signals,
        "score": round(score, 2),
        "max_score": round(max_score, 2),
        "score_pct": round(score_pct, 1),
        "support_resistance": sr,
    }


def scan_for_intraday_tips(symbols, top_n=10):
    """Scan multiple symbols and return the best intraday opportunities."""
    from .market_data import fetch_market_data

    opportunities = []
    for symbol in symbols:
        try:
            df = fetch_market_data(symbol, period="3mo", interval="1d")
            if df is not None and not df.empty:
                tip = generate_intraday_tips(symbol, df)
                if tip["action"] != "WAIT":
                    opportunities.append(tip)
        except Exception as e:
            print(f"Error scanning {symbol}: {e}")

    opportunities.sort(key=lambda x: x["confidence"], reverse=True)
    return opportunities[:top_n]
