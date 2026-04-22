"""
Backtesting Engine — Multiple trading strategies with simulation capabilities.
Strategies: Confluence, EMA Crossover, RSI Reversal, Mean Reversion
"""

import pandas as pd
import numpy as np
from .indicators import calculate_all_indicators


def _generate_confluence_signals(df):
    """Multi-indicator confluence signals (original strategy)."""
    result = df.copy()
    result["Signal"] = 0

    for i in range(30, len(result)):
        row = result.iloc[i]
        score = 0

        rsi = row.get("RSI")
        if rsi is not None and not pd.isna(rsi):
            if rsi < 30: score += 1.5
            elif rsi < 40: score += 0.5
            elif rsi > 70: score -= 1.5
            elif rsi > 60: score -= 0.5

        macd = row.get("MACD")
        macd_sig = row.get("MACD_Signal")
        if macd is not None and macd_sig is not None and not pd.isna(macd) and not pd.isna(macd_sig):
            if macd > macd_sig: score += 1
            else: score -= 1

        ema9 = row.get("EMA_9")
        ema21 = row.get("EMA_21")
        if ema9 is not None and ema21 is not None and not pd.isna(ema9) and not pd.isna(ema21):
            if ema9 > ema21: score += 1
            else: score -= 1

        close = row.get("Close")
        bb_lower = row.get("BB_Lower")
        bb_upper = row.get("BB_Upper")
        if all(v is not None and not pd.isna(v) for v in [close, bb_lower, bb_upper]):
            bb_range = bb_upper - bb_lower
            if bb_range > 0:
                pct = (close - bb_lower) / bb_range
                if pct < 0.1: score += 1.5
                elif pct > 0.9: score -= 1.5

        st_dir = row.get("Supertrend_Dir")
        if st_dir is not None and not pd.isna(st_dir):
            if st_dir == 1: score += 1
            else: score -= 1

        if score >= 2.5:
            result.iloc[i, result.columns.get_loc("Signal")] = 1
        elif score <= -2.5:
            result.iloc[i, result.columns.get_loc("Signal")] = -1

    return result


def _generate_ema_crossover_signals(df):
    """EMA 9/21 crossover strategy: Buy when 9 crosses above 21, sell when crosses below."""
    result = df.copy()
    result["Signal"] = 0

    for i in range(1, len(result)):
        ema9 = result.iloc[i].get("EMA_9")
        ema21 = result.iloc[i].get("EMA_21")
        prev_ema9 = result.iloc[i - 1].get("EMA_9")
        prev_ema21 = result.iloc[i - 1].get("EMA_21")

        if all(v is not None and not pd.isna(v) for v in [ema9, ema21, prev_ema9, prev_ema21]):
            # Golden crossover
            if prev_ema9 <= prev_ema21 and ema9 > ema21:
                result.iloc[i, result.columns.get_loc("Signal")] = 1
            # Death crossover
            elif prev_ema9 >= prev_ema21 and ema9 < ema21:
                result.iloc[i, result.columns.get_loc("Signal")] = -1

    return result


def _generate_rsi_reversal_signals(df):
    """RSI reversal strategy: Buy when RSI exits oversold, sell when exits overbought."""
    result = df.copy()
    result["Signal"] = 0

    for i in range(1, len(result)):
        rsi = result.iloc[i].get("RSI")
        prev_rsi = result.iloc[i - 1].get("RSI")

        if rsi is not None and prev_rsi is not None and not pd.isna(rsi) and not pd.isna(prev_rsi):
            # RSI exits oversold (crosses above 30)
            if prev_rsi < 30 and rsi >= 30:
                result.iloc[i, result.columns.get_loc("Signal")] = 1
            # RSI exits overbought (crosses below 70)
            elif prev_rsi > 70 and rsi <= 70:
                result.iloc[i, result.columns.get_loc("Signal")] = -1

    return result


def _generate_mean_reversion_signals(df):
    """Mean reversion using Bollinger Bands: Buy at lower band, sell at upper band."""
    result = df.copy()
    result["Signal"] = 0

    for i in range(1, len(result)):
        close = result.iloc[i].get("Close")
        prev_close = result.iloc[i - 1].get("Close")
        bb_lower = result.iloc[i].get("BB_Lower")
        bb_upper = result.iloc[i].get("BB_Upper")
        bb_mid = result.iloc[i].get("BB_Mid")
        rsi = result.iloc[i].get("RSI")

        if all(v is not None and not pd.isna(v) for v in [close, bb_lower, bb_upper, bb_mid]):
            # Buy: Price touches or goes below lower band AND RSI < 40
            if close <= bb_lower and (rsi is None or pd.isna(rsi) or rsi < 40):
                result.iloc[i, result.columns.get_loc("Signal")] = 1
            # Sell: Price touches or goes above upper band AND RSI > 60
            elif close >= bb_upper and (rsi is None or pd.isna(rsi) or rsi > 60):
                result.iloc[i, result.columns.get_loc("Signal")] = -1

    return result


def _generate_supertrend_macd_signals(df):
    """Supertrend + MACD combo: Both must agree for a signal."""
    result = df.copy()
    result["Signal"] = 0

    for i in range(1, len(result)):
        st_dir = result.iloc[i].get("Supertrend_Dir")
        macd = result.iloc[i].get("MACD")
        macd_sig = result.iloc[i].get("MACD_Signal")
        prev_macd = result.iloc[i - 1].get("MACD")
        prev_macd_sig = result.iloc[i - 1].get("MACD_Signal")

        if all(v is not None and not pd.isna(v) for v in [st_dir, macd, macd_sig]):
            # Buy: Supertrend bullish + MACD crossover
            if st_dir == 1:
                if prev_macd is not None and prev_macd_sig is not None:
                    if not pd.isna(prev_macd) and not pd.isna(prev_macd_sig):
                        if prev_macd <= prev_macd_sig and macd > macd_sig:
                            result.iloc[i, result.columns.get_loc("Signal")] = 1
            # Sell: Supertrend bearish + MACD crossunder
            elif st_dir == -1:
                if prev_macd is not None and prev_macd_sig is not None:
                    if not pd.isna(prev_macd) and not pd.isna(prev_macd_sig):
                        if prev_macd >= prev_macd_sig and macd < macd_sig:
                            result.iloc[i, result.columns.get_loc("Signal")] = -1

    return result


STRATEGIES = {
    "confluence": {
        "name": "Multi-Indicator Confluence",
        "description": "Uses RSI, MACD, EMA, Bollinger Bands, and Supertrend together",
        "func": _generate_confluence_signals,
    },
    "ema_crossover": {
        "name": "EMA 9/21 Crossover",
        "description": "Buy on golden crossover (EMA9 > EMA21), sell on death crossover",
        "func": _generate_ema_crossover_signals,
    },
    "rsi_reversal": {
        "name": "RSI Reversal",
        "description": "Buy when RSI exits oversold (<30), sell when exits overbought (>70)",
        "func": _generate_rsi_reversal_signals,
    },
    "mean_reversion": {
        "name": "Bollinger Band Mean Reversion",
        "description": "Buy at lower Bollinger Band, sell at upper band (with RSI filter)",
        "func": _generate_mean_reversion_signals,
    },
    "supertrend_macd": {
        "name": "Supertrend + MACD Combo",
        "description": "Requires both Supertrend direction and MACD crossover to agree",
        "func": _generate_supertrend_macd_signals,
    },
}


def get_available_strategies():
    """Return list of available strategies for the UI."""
    return [
        {"id": k, "name": v["name"], "description": v["description"]}
        for k, v in STRATEGIES.items()
    ]


def run_backtest(df, initial_capital=100000, strategy="confluence",
                 stop_loss_pct=3.0, take_profit_pct=6.0, position_size_pct=20.0):
    """
    Run a backtest simulation on historical OHLCV data.
    """
    if df is None or df.empty or len(df) < 50:
        return {
            "error": "Insufficient data for backtesting (need at least 50 data points)",
            "summary": {},
            "equity_curve": [],
            "trades": [],
        }

    # Calculate indicators
    df_indicators = calculate_all_indicators(df)

    # Generate signals based on selected strategy
    strat = STRATEGIES.get(strategy, STRATEGIES["confluence"])
    df_signals = strat["func"](df_indicators)

    # ─── Run Simulation ───
    capital = initial_capital
    position = None
    trades = []
    equity_curve = []
    peak_equity = initial_capital
    max_drawdown = 0

    for i in range(len(df_signals)):
        row = df_signals.iloc[i]
        current_time = row.name.strftime("%Y-%m-%d") if hasattr(row.name, "strftime") else str(row.name)
        close = float(row["Close"])
        signal = int(row.get("Signal", 0))

        # Check stop loss / take profit on open position
        if position is not None:
            pnl_pct = ((close - position["entry_price"]) / position["entry_price"]) * 100

            if pnl_pct <= -stop_loss_pct:
                pnl = (close - position["entry_price"]) * position["qty"]
                capital += close * position["qty"]
                trades.append({
                    "entry_date": position["entry_date"],
                    "exit_date": current_time,
                    "entry_price": position["entry_price"],
                    "exit_price": round(close, 2),
                    "qty": position["qty"],
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "exit_reason": "Stop Loss",
                    "type": "LONG",
                })
                position = None

            elif pnl_pct >= take_profit_pct:
                pnl = (close - position["entry_price"]) * position["qty"]
                capital += close * position["qty"]
                trades.append({
                    "entry_date": position["entry_date"],
                    "exit_date": current_time,
                    "entry_price": position["entry_price"],
                    "exit_price": round(close, 2),
                    "qty": position["qty"],
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "exit_reason": "Take Profit",
                    "type": "LONG",
                })
                position = None

            elif signal == -1:
                pnl = (close - position["entry_price"]) * position["qty"]
                capital += close * position["qty"]
                trades.append({
                    "entry_date": position["entry_date"],
                    "exit_date": current_time,
                    "entry_price": position["entry_price"],
                    "exit_price": round(close, 2),
                    "qty": position["qty"],
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "exit_reason": "Sell Signal",
                    "type": "LONG",
                })
                position = None

        elif signal == 1 and position is None:
            invest_amount = capital * (position_size_pct / 100)
            if invest_amount > 0 and close > 0:
                qty = int(invest_amount / close)
                if qty > 0:
                    capital -= close * qty
                    position = {
                        "entry_date": current_time,
                        "entry_price": round(close, 2),
                        "qty": qty,
                    }

        portfolio_value = capital
        if position is not None:
            portfolio_value += close * position["qty"]

        equity_curve.append({
            "time": current_time,
            "value": round(portfolio_value, 2),
        })

        if portfolio_value > peak_equity:
            peak_equity = portfolio_value
        drawdown = ((peak_equity - portfolio_value) / peak_equity) * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    # Close any remaining position
    if position is not None:
        close = float(df_signals.iloc[-1]["Close"])
        pnl = (close - position["entry_price"]) * position["qty"]
        pnl_pct = ((close - position["entry_price"]) / position["entry_price"]) * 100
        capital += close * position["qty"]
        trades.append({
            "entry_date": position["entry_date"],
            "exit_date": equity_curve[-1]["time"],
            "entry_price": position["entry_price"],
            "exit_price": round(close, 2),
            "qty": position["qty"],
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "exit_reason": "End of Backtest",
            "type": "LONG",
        })

    # ─── Calculate Summary Statistics ───
    final_value = equity_curve[-1]["value"] if equity_curve else initial_capital
    total_return = ((final_value - initial_capital) / initial_capital) * 100

    winning_trades = [t for t in trades if t["pnl"] > 0]
    losing_trades = [t for t in trades if t["pnl"] <= 0]

    total_trades = len(trades)
    win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0

    avg_win = np.mean([t["pnl"] for t in winning_trades]) if winning_trades else 0
    avg_loss = np.mean([abs(t["pnl"]) for t in losing_trades]) if losing_trades else 0
    profit_factor = (sum(t["pnl"] for t in winning_trades) / abs(sum(t["pnl"] for t in losing_trades))) if losing_trades and sum(t["pnl"] for t in losing_trades) != 0 else float("inf")

    # Sharpe Ratio
    if len(equity_curve) > 1:
        returns = []
        for j in range(1, len(equity_curve)):
            daily_ret = (equity_curve[j]["value"] - equity_curve[j-1]["value"]) / equity_curve[j-1]["value"]
            returns.append(daily_ret)
        if returns:
            avg_return = np.mean(returns)
            std_return = np.std(returns) if np.std(returns) > 0 else 1e-10
            sharpe = (avg_return / std_return) * np.sqrt(252)
        else:
            sharpe = 0
    else:
        sharpe = 0

    summary = {
        "initial_capital": initial_capital,
        "final_value": round(final_value, 2),
        "total_return_pct": round(total_return, 2),
        "total_return_inr": round(final_value - initial_capital, 2),
        "total_trades": total_trades,
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate": round(win_rate, 1),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else "∞",
        "max_drawdown": round(max_drawdown, 2),
        "sharpe_ratio": round(sharpe, 2),
        "strategy": strat["name"],
        "strategy_id": strategy,
        "stop_loss_pct": stop_loss_pct,
        "take_profit_pct": take_profit_pct,
        "position_size_pct": position_size_pct,
    }

    return {
        "summary": summary,
        "equity_curve": equity_curve,
        "trades": trades,
    }
