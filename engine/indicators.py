"""
Technical Indicators Module — Computes a comprehensive set of trading indicators.
Enhanced with Williams %R, CCI, Fibonacci Levels.
"""

import pandas as pd
import pandas_ta as ta
import numpy as np


def calculate_all_indicators(df):
    """
    Calculate all technical indicators on the given OHLCV DataFrame.
    Returns a new DataFrame with all indicator columns added.
    """
    if df is None or df.empty or len(df) < 30:
        return df

    result = df.copy()

    # ─── Moving Averages ───
    result["EMA_9"] = ta.ema(result["Close"], length=9)
    result["EMA_21"] = ta.ema(result["Close"], length=21)
    result["EMA_50"] = ta.ema(result["Close"], length=50)
    result["EMA_200"] = ta.ema(result["Close"], length=200)
    result["SMA_20"] = ta.sma(result["Close"], length=20)
    result["SMA_50"] = ta.sma(result["Close"], length=50)
    result["SMA_200"] = ta.sma(result["Close"], length=200)

    # ─── RSI ───
    result["RSI"] = ta.rsi(result["Close"], length=14)

    # ─── MACD ───
    macd = ta.macd(result["Close"], fast=12, slow=26, signal=9)
    if macd is not None and not macd.empty:
        result["MACD"] = macd.iloc[:, 0]
        result["MACD_Signal"] = macd.iloc[:, 1] if macd.shape[1] > 1 else None
        result["MACD_Hist"] = macd.iloc[:, 2] if macd.shape[1] > 2 else None

    # ─── Bollinger Bands ───
    bbands = ta.bbands(result["Close"], length=20, std=2)
    if bbands is not None and not bbands.empty:
        result["BB_Lower"] = bbands.iloc[:, 0]
        result["BB_Mid"] = bbands.iloc[:, 1]
        result["BB_Upper"] = bbands.iloc[:, 2]
        if bbands.shape[1] > 3:
            result["BB_Width"] = bbands.iloc[:, 3]
        if bbands.shape[1] > 4:
            result["BB_Pct"] = bbands.iloc[:, 4]

    # ─── Stochastic Oscillator ───
    stoch = ta.stoch(result["High"], result["Low"], result["Close"], k=14, d=3, smooth_k=3)
    if stoch is not None and not stoch.empty:
        result["STOCH_K"] = stoch.iloc[:, 0]
        result["STOCH_D"] = stoch.iloc[:, 1]

    # ─── ADX (Average Directional Index) ───
    adx = ta.adx(result["High"], result["Low"], result["Close"], length=14)
    if adx is not None and not adx.empty:
        result["ADX"] = adx.iloc[:, 0]
        result["DI_Plus"] = adx.iloc[:, 1] if adx.shape[1] > 1 else None
        result["DI_Minus"] = adx.iloc[:, 2] if adx.shape[1] > 2 else None

    # ─── ATR (Average True Range) ───
    result["ATR"] = ta.atr(result["High"], result["Low"], result["Close"], length=14)

    # ─── OBV (On-Balance Volume) ───
    result["OBV"] = ta.obv(result["Close"], result["Volume"])

    # ─── VWAP (Volume Weighted Average Price) ───
    try:
        result["VWAP"] = ta.vwap(result["High"], result["Low"], result["Close"], result["Volume"])
    except Exception:
        result["VWAP"] = (result["High"] + result["Low"] + result["Close"]) / 3

    # ─── Supertrend ───
    try:
        supertrend = ta.supertrend(result["High"], result["Low"], result["Close"], length=10, multiplier=3)
        if supertrend is not None and not supertrend.empty:
            result["Supertrend"] = supertrend.iloc[:, 0]
            result["Supertrend_Dir"] = supertrend.iloc[:, 1]
    except Exception:
        pass

    # ─── Ichimoku Cloud ───
    try:
        ichimoku_vals, ichimoku_span = ta.ichimoku(result["High"], result["Low"], result["Close"])
        if ichimoku_vals is not None and not ichimoku_vals.empty:
            result["Ichimoku_Tenkan"] = ichimoku_vals.iloc[:, 0]
            result["Ichimoku_Kijun"] = ichimoku_vals.iloc[:, 1]
            if ichimoku_vals.shape[1] > 2:
                result["Ichimoku_SenkouA"] = ichimoku_vals.iloc[:, 2]
            if ichimoku_vals.shape[1] > 3:
                result["Ichimoku_SenkouB"] = ichimoku_vals.iloc[:, 3]
    except Exception:
        pass

    # ═══ NEW INDICATORS ═══

    # ─── Williams %R ───
    try:
        result["WILLR"] = ta.willr(result["High"], result["Low"], result["Close"], length=14)
    except Exception:
        pass

    # ─── CCI (Commodity Channel Index) ───
    try:
        result["CCI"] = ta.cci(result["High"], result["Low"], result["Close"], length=20)
    except Exception:
        pass

    # ─── ROC (Rate of Change) ───
    try:
        result["ROC"] = ta.roc(result["Close"], length=12)
    except Exception:
        pass

    # ─── MFI (Money Flow Index) ───
    try:
        result["MFI"] = ta.mfi(result["High"], result["Low"], result["Close"], result["Volume"], length=14)
    except Exception:
        pass

    # ─── CMF (Chaikin Money Flow) ───
    try:
        result["CMF"] = ta.cmf(result["High"], result["Low"], result["Close"], result["Volume"], length=20)
    except Exception:
        pass

    return result


def calculate_fibonacci_levels(df, lookback=60):
    """
    Calculate Fibonacci retracement levels from recent high/low.
    """
    if df is None or len(df) < lookback:
        lookback = len(df) if df is not None else 0

    if lookback < 2:
        return {}

    recent = df.tail(lookback)
    high = float(recent["High"].max())
    low = float(recent["Low"].min())
    diff = high - low

    levels = {
        "high": round(high, 2),
        "low": round(low, 2),
        "fib_0": round(high, 2),             # 0%
        "fib_236": round(high - 0.236 * diff, 2),  # 23.6%
        "fib_382": round(high - 0.382 * diff, 2),  # 38.2%
        "fib_500": round(high - 0.500 * diff, 2),  # 50%
        "fib_618": round(high - 0.618 * diff, 2),  # 61.8%
        "fib_786": round(high - 0.786 * diff, 2),  # 78.6%
        "fib_100": round(low, 2),             # 100%
    }

    # Extension levels
    levels["fib_ext_127"] = round(high + 0.272 * diff, 2)
    levels["fib_ext_162"] = round(high + 0.618 * diff, 2)
    levels["fib_ext_200"] = round(high + 1.000 * diff, 2)

    return levels


def get_indicator_summary(df):
    """Get the latest values of all indicators as a JSON-serializable dictionary."""
    if df is None or df.empty:
        return {}

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    def safe_val(val):
        if pd.isna(val):
            return None
        return round(float(val), 2)

    summary = {
        "price": {
            "close": safe_val(latest.get("Close")),
            "open": safe_val(latest.get("Open")),
            "high": safe_val(latest.get("High")),
            "low": safe_val(latest.get("Low")),
            "volume": int(latest.get("Volume", 0)),
            "change": safe_val(latest.get("Close", 0) - prev.get("Close", 0)),
            "changePct": safe_val(
                ((latest.get("Close", 0) - prev.get("Close", 0)) / prev.get("Close", 1)) * 100
            ),
        },
        "movingAverages": {
            "EMA_9": safe_val(latest.get("EMA_9")),
            "EMA_21": safe_val(latest.get("EMA_21")),
            "EMA_50": safe_val(latest.get("EMA_50")),
            "EMA_200": safe_val(latest.get("EMA_200")),
            "SMA_20": safe_val(latest.get("SMA_20")),
            "SMA_50": safe_val(latest.get("SMA_50")),
            "SMA_200": safe_val(latest.get("SMA_200")),
        },
        "oscillators": {
            "RSI": safe_val(latest.get("RSI")),
            "MACD": safe_val(latest.get("MACD")),
            "MACD_Signal": safe_val(latest.get("MACD_Signal")),
            "MACD_Hist": safe_val(latest.get("MACD_Hist")),
            "STOCH_K": safe_val(latest.get("STOCH_K")),
            "STOCH_D": safe_val(latest.get("STOCH_D")),
            "ADX": safe_val(latest.get("ADX")),
            "DI_Plus": safe_val(latest.get("DI_Plus")),
            "DI_Minus": safe_val(latest.get("DI_Minus")),
            "Williams_%R": safe_val(latest.get("WILLR")),
            "CCI": safe_val(latest.get("CCI")),
            "ROC": safe_val(latest.get("ROC")),
            "MFI": safe_val(latest.get("MFI")),
        },
        "volatility": {
            "ATR": safe_val(latest.get("ATR")),
            "BB_Upper": safe_val(latest.get("BB_Upper")),
            "BB_Mid": safe_val(latest.get("BB_Mid")),
            "BB_Lower": safe_val(latest.get("BB_Lower")),
            "BB_Width": safe_val(latest.get("BB_Width")),
        },
        "volume_indicators": {
            "OBV": safe_val(latest.get("OBV")),
            "VWAP": safe_val(latest.get("VWAP")),
            "CMF": safe_val(latest.get("CMF")),
        },
        "trend": {
            "Supertrend": safe_val(latest.get("Supertrend")),
            "Supertrend_Dir": safe_val(latest.get("Supertrend_Dir")),
        },
        "fibonacci": calculate_fibonacci_levels(df),
    }

    return summary


def get_indicator_series(df, indicator_names):
    """
    Get time-series data for specific indicators to overlay on charts.
    """
    if df is None or df.empty:
        return {}

    result = {}
    for name in indicator_names:
        if name in df.columns:
            series = []
            for idx, row in df.iterrows():
                val = row[name]
                if not pd.isna(val):
                    series.append({
                        "time": idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx),
                        "value": round(float(val), 2)
                    })
            result[name] = series

    return result
