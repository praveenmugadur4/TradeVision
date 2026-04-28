"""
Paper Trading Engine — Simulated trades to validate predictions.

Auto-picks top stocks from golden picks scan, places dummy trades with
conservative targets (₹1-2 profit/share), and tracks P&L throughout the day.
"""

import json
import os
import math
import yfinance as yf
from datetime import datetime, date
from .golden_picks import get_golden_picks

TRADE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "paper_trades.json")
HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "paper_trade_history.json")
DEFAULT_QTY = 1000
CONSERVATIVE_TARGET_PTS = 2  # Take profit at just ₹2 per share


def _load_trades():
    """Load active paper trades from file."""
    if os.path.exists(TRADE_FILE):
        try:
            with open(TRADE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"date": str(date.today()), "trades": [], "summary": {}}


def _save_trades(data):
    """Save paper trades to file."""
    with open(TRADE_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _load_history():
    """Load historical trade results."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_history(history):
    """Save trade history."""
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2, default=str)


def _safe(val):
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
        return None
    return float(val)


def start_paper_trading(qty=None, target_pts=None, top_n=5, force_restart=False):
    """
    Run golden picks scan and auto-place paper trades on top stocks.
    
    Args:
        qty: Quantity per trade (default 1000)
        target_pts: Points target per trade (default 2)
        top_n: Number of stocks to pick (default 5)
        force_restart: If True, close existing trades and start fresh
    
    Returns:
        dict with trades placed
    """
    quantity = qty or DEFAULT_QTY
    target_points = target_pts or CONSERVATIVE_TARGET_PTS
    today = str(date.today())

    # Check if we already have trades for today
    existing = _load_trades()
    if existing.get("date") == today and existing.get("trades"):
        if not force_restart:
            return {
                "status": "already_active",
                "message": f"You already have {len(existing['trades'])} paper trades running today. Click '🔁 Reset & Restart' to start fresh.",
                "data": existing,
            }
        else:
            # Save existing trades to history before resetting
            _save_to_history(existing)

    # Run golden picks scan
    picks = get_golden_picks(top_n=top_n)

    if not picks:
        return {
            "status": "no_picks",
            "message": "No golden picks found today. Market may be sideways.",
            "data": {"date": today, "trades": [], "summary": {}},
        }

    trades = []
    for pick in picks:
        entry = pick["entry"]
        direction = pick["direction"]

        if direction == "BUY":
            sell_target = round(entry + target_points, 2)
            stop_loss = round(entry - (target_points * 2), 2)
            max_profit = round((sell_target - entry) * quantity, 2)
            max_loss = round((entry - stop_loss) * quantity, 2)
        else:
            sell_target = round(entry - target_points, 2)
            stop_loss = round(entry + (target_points * 2), 2)
            max_profit = round((entry - sell_target) * quantity, 2)
            max_loss = round((stop_loss - entry) * quantity, 2)

        trade = {
            "id": f"{pick['symbol']}_{today}_{datetime.now().strftime('%H%M%S')}",
            "symbol": pick["symbol"],
            "name": pick["name"],
            "direction": direction,
            "entry_price": entry,
            "target_price": sell_target,
            "stop_loss": stop_loss,
            "quantity": quantity,
            "target_points": target_points,
            "confidence": pick["confidence"],
            "status": "ACTIVE",
            "current_price": entry,
            "pnl": 0,
            "pnl_pct": 0,
            "max_profit": max_profit,
            "max_loss": max_loss,
            "entry_time": datetime.now().strftime("%H:%M:%S"),
            "exit_time": None,
            "exit_price": None,
            "reasons": pick.get("reasons", [])[:3],
        }
        trades.append(trade)

    trade_data = {
        "date": today,
        "trades": trades,
        "summary": {
            "total_trades": len(trades),
            "active": len(trades),
            "target_hit": 0,
            "sl_hit": 0,
            "total_pnl": 0,
            "total_investment": sum(t["entry_price"] * t["quantity"] for t in trades),
            "started_at": datetime.now().strftime("%H:%M:%S"),
        }
    }

    _save_trades(trade_data)

    return {
        "status": "started",
        "message": f"Paper trading started! {len(trades)} trades placed with qty={quantity}, target=₹{target_points}.",
        "data": trade_data,
    }


def _save_to_history(data):
    """Save a trade session to history (used when resetting mid-day)."""
    # Close any remaining active trades at current price
    for trade in data.get("trades", []):
        if trade["status"] == "ACTIVE":
            trade["status"] = "CLOSED"
            trade["exit_price"] = trade["current_price"]
            trade["exit_time"] = datetime.now().strftime("%H:%M:%S")

    total_pnl = sum(t["pnl"] for t in data.get("trades", []))
    winners = sum(1 for t in data.get("trades", []) if t["pnl"] > 0)
    total = len(data.get("trades", []))
    data["summary"]["total_pnl"] = round(total_pnl, 2)
    data["summary"]["winners"] = winners
    data["summary"]["win_rate"] = round((winners / total) * 100, 1) if total > 0 else 0
    data["summary"]["closed_at"] = datetime.now().strftime("%H:%M:%S")

    history = _load_history()
    history.append(data)
    history = history[-30:]
    _save_history(history)


def update_paper_trades():
    """
    Check current prices and update P&L for all active paper trades.
    Auto-closes trades that hit target or stop loss.
    """
    data = _load_trades()
    today = str(date.today())

    if data.get("date") != today or not data.get("trades"):
        return data

    active = 0
    target_hit = 0
    sl_hit = 0
    total_pnl = 0

    for trade in data["trades"]:
        # Fetch LIVE current price for ALL trades (bypass cache)
        try:
            ticker = yf.Ticker(trade["symbol"])
            try:
                info = ticker.fast_info
                current = _safe(float(info.get("lastPrice", 0) or info.get("last_price", 0)))
            except Exception:
                current = None

            if not current or current == 0:
                df = ticker.history(period="1d", interval="2m")
                if df is not None and not df.empty:
                    current = _safe(float(df["Close"].iloc[-1]))

            if current and current > 0:
                trade["current_price"] = round(current, 2)
        except Exception:
            pass

        if trade["status"] not in ("ACTIVE",):
            # Already closed — just add to totals, but current_price is updated above
            total_pnl += trade["pnl"]
            if trade["status"] == "TARGET_HIT":
                target_hit += 1
            elif trade["status"] == "SL_HIT":
                sl_hit += 1
            continue

        entry = trade["entry_price"]
        current = trade["current_price"]
        qty = trade["quantity"]
        direction = trade["direction"]
        target = trade["target_price"]
        sl = trade["stop_loss"]

        # Calculate P&L
        if direction == "BUY":
            pnl = round((current - entry) * qty, 2)
            # Check if target hit
            if current >= target:
                trade["status"] = "TARGET_HIT"
                trade["exit_price"] = target
                trade["exit_time"] = datetime.now().strftime("%H:%M:%S")
                trade["pnl"] = round((target - entry) * qty, 2)
                target_hit += 1
            elif current <= sl:
                trade["status"] = "SL_HIT"
                trade["exit_price"] = sl
                trade["exit_time"] = datetime.now().strftime("%H:%M:%S")
                trade["pnl"] = round((sl - entry) * qty, 2)
                sl_hit += 1
            else:
                trade["pnl"] = pnl
                active += 1
        else:  # SELL/SHORT
            pnl = round((entry - current) * qty, 2)
            if current <= target:
                trade["status"] = "TARGET_HIT"
                trade["exit_price"] = target
                trade["exit_time"] = datetime.now().strftime("%H:%M:%S")
                trade["pnl"] = round((entry - target) * qty, 2)
                target_hit += 1
            elif current >= sl:
                trade["status"] = "SL_HIT"
                trade["exit_price"] = sl
                trade["exit_time"] = datetime.now().strftime("%H:%M:%S")
                trade["pnl"] = round((entry - sl) * qty, 2)
                sl_hit += 1
            else:
                trade["pnl"] = pnl
                active += 1

        trade["pnl_pct"] = round((trade["pnl"] / (entry * qty)) * 100, 2) if entry * qty > 0 else 0
        total_pnl += trade["pnl"]

    # Update summary
    data["summary"]["active"] = active
    data["summary"]["target_hit"] = target_hit
    data["summary"]["sl_hit"] = sl_hit
    data["summary"]["total_pnl"] = round(total_pnl, 2)
    data["summary"]["last_updated"] = datetime.now().strftime("%H:%M:%S")
    data["summary"]["win_rate"] = round(
        (target_hit / (target_hit + sl_hit)) * 100, 1
    ) if (target_hit + sl_hit) > 0 else 0

    _save_trades(data)
    return data


def close_day():
    """
    Close all remaining active trades at current price and save to history.
    Call this at end of trading day (3:30 PM).
    """
    data = update_paper_trades()
    today = str(date.today())

    if data.get("date") != today:
        return {"status": "no_trades", "message": "No trades to close today."}

    # Close all remaining active trades at current price
    for trade in data["trades"]:
        if trade["status"] == "ACTIVE":
            trade["status"] = "CLOSED"
            trade["exit_price"] = trade["current_price"]
            trade["exit_time"] = datetime.now().strftime("%H:%M:%S")

    # Recalculate summary
    total_pnl = sum(t["pnl"] for t in data["trades"])
    winners = sum(1 for t in data["trades"] if t["pnl"] > 0)
    losers = sum(1 for t in data["trades"] if t["pnl"] < 0)
    total = len(data["trades"])

    data["summary"]["active"] = 0
    data["summary"]["total_pnl"] = round(total_pnl, 2)
    data["summary"]["winners"] = winners
    data["summary"]["losers"] = losers
    data["summary"]["win_rate"] = round((winners / total) * 100, 1) if total > 0 else 0
    data["summary"]["closed_at"] = datetime.now().strftime("%H:%M:%S")

    _save_trades(data)

    # Save to history
    history = _load_history()
    history.append(data)
    # Keep only last 30 days
    history = history[-30:]
    _save_history(history)

    return {
        "status": "closed",
        "message": f"Day closed. P&L: ₹{total_pnl:,.2f} | Win rate: {data['summary']['win_rate']}%",
        "data": data,
    }


def get_trade_history():
    """Get historical paper trade results."""
    return _load_history()


def get_performance_stats():
    """Calculate overall performance statistics across all trading days."""
    history = _load_history()

    if not history:
        return {
            "total_days": 0,
            "message": "No trading history yet. Start paper trading to track performance!",
        }

    total_pnl = 0
    total_trades = 0
    total_winners = 0
    total_target_hit = 0
    total_sl_hit = 0
    winning_days = 0
    daily_pnls = []

    for day in history:
        s = day.get("summary", {})
        day_pnl = s.get("total_pnl", 0)
        total_pnl += day_pnl
        total_trades += s.get("total_trades", 0)
        total_winners += s.get("winners", 0)
        total_target_hit += s.get("target_hit", 0)
        total_sl_hit += s.get("sl_hit", 0)
        daily_pnls.append(day_pnl)
        if day_pnl > 0:
            winning_days += 1

    total_days = len(history)
    avg_daily_pnl = round(total_pnl / total_days, 2) if total_days > 0 else 0

    return {
        "total_days": total_days,
        "total_pnl": round(total_pnl, 2),
        "avg_daily_pnl": avg_daily_pnl,
        "total_trades": total_trades,
        "total_winners": total_winners,
        "win_rate": round((total_winners / total_trades) * 100, 1) if total_trades > 0 else 0,
        "winning_days": winning_days,
        "losing_days": total_days - winning_days,
        "day_win_rate": round((winning_days / total_days) * 100, 1) if total_days > 0 else 0,
        "best_day": round(max(daily_pnls), 2) if daily_pnls else 0,
        "worst_day": round(min(daily_pnls), 2) if daily_pnls else 0,
        "target_hit_rate": round((total_target_hit / total_trades) * 100, 1) if total_trades > 0 else 0,
    }
