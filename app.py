# -*- coding: utf-8 -*-
"""
TradeVision — Flask Server (Enhanced)
Premium Trading Dashboard with Backtesting, Alerts, Intraday Tips & Stock Categories
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from engine.market_data import (
    fetch_market_data, get_stock_info, search_stocks, dataframe_to_json,
    get_stocks_by_category, get_category_symbols,
    LARGE_CAP_STOCKS, MID_CAP_STOCKS, SMALL_CAP_STOCKS, PENNY_STOCKS
)
from engine.indicators import calculate_all_indicators, get_indicator_summary, get_indicator_series
from engine.signals import generate_signals
from engine.backtester import run_backtest, get_available_strategies
from engine.intraday import generate_intraday_tips, scan_for_intraday_tips
from engine import telegram_bot
from engine.golden_picks import get_golden_picks, get_weekly_picks, calculate_cpr
from engine.market_pulse import get_market_pulse, get_analyst_recommendations, get_news_sentiment
from engine.paper_trader import start_paper_trading, update_paper_trades, close_day, get_trade_history, get_performance_stats
import json
import math

app = Flask(__name__)
CORS(app)


def sanitize_for_json(obj):
    """Recursively replace NaN/Infinity with None in dicts/lists."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    return obj


def safe_jsonify(data):
    """Jsonify data after sanitizing NaN/Infinity values."""
    return jsonify(sanitize_for_json(data))


@app.route("/")
def index():
    return render_template("index.html")


# ─── API ENDPOINTS ───

@app.route("/api/search")
def api_search():
    query = request.args.get("q", "")
    if not query or len(query) < 2:
        return jsonify([])
    results = search_stocks(query)
    return jsonify(results)


@app.route("/api/stock-info")
def api_stock_info():
    symbol = request.args.get("symbol", "RELIANCE.NS")
    info = get_stock_info(symbol)
    return safe_jsonify(info)


@app.route("/api/market-data")
def api_market_data():
    symbol = request.args.get("symbol", "RELIANCE.NS")
    period = request.args.get("period", "1y")
    interval = request.args.get("interval", "1d")

    df = fetch_market_data(symbol, period=period, interval=interval)
    if df is None:
        return safe_jsonify({"error": "No data found", "data": []})

    data = dataframe_to_json(df)
    return safe_jsonify({"symbol": symbol, "data": data})


@app.route("/api/indicators")
def api_indicators():
    symbol = request.args.get("symbol", "RELIANCE.NS")
    period = request.args.get("period", "1y")
    interval = request.args.get("interval", "1d")

    df = fetch_market_data(symbol, period=period, interval=interval)
    if df is None:
        return safe_jsonify({"error": "No data found"})

    df_ind = calculate_all_indicators(df)
    summary = get_indicator_summary(df_ind)

    overlay_indicators = [
        "EMA_9", "EMA_21", "EMA_50", "SMA_200",
        "BB_Upper", "BB_Mid", "BB_Lower", "Supertrend"
    ]
    panel_indicators = [
        "RSI", "MACD", "MACD_Signal", "MACD_Hist",
        "STOCH_K", "STOCH_D", "ADX", "OBV",
        "WILLR", "CCI", "MFI"
    ]

    overlay_series = get_indicator_series(df_ind, overlay_indicators)
    panel_series = get_indicator_series(df_ind, panel_indicators)

    return safe_jsonify({
        "symbol": symbol,
        "summary": summary,
        "overlay_series": overlay_series,
        "panel_series": panel_series,
    })


@app.route("/api/signals")
def api_signals():
    symbol = request.args.get("symbol", "RELIANCE.NS")
    period = request.args.get("period", "1y")
    interval = request.args.get("interval", "1d")

    df = fetch_market_data(symbol, period=period, interval=interval)
    if df is None:
        return jsonify({"error": "No data found"})

    df_ind = calculate_all_indicators(df)
    signals = generate_signals(df_ind)
    signals["symbol"] = symbol
    return safe_jsonify(signals)


@app.route("/api/backtest", methods=["POST"])
def api_backtest():
    data = request.get_json() or {}
    symbol = data.get("symbol", "RELIANCE.NS")
    period = data.get("period", "2y")
    initial_capital = float(data.get("initial_capital", 100000))
    stop_loss = float(data.get("stop_loss", 3.0))
    take_profit = float(data.get("take_profit", 6.0))
    position_size = float(data.get("position_size", 20.0))
    strategy = data.get("strategy", "confluence")

    df = fetch_market_data(symbol, period=period, interval="1d")
    if df is None:
        return jsonify({"error": "No data found for backtesting"})

    result = run_backtest(
        df,
        initial_capital=initial_capital,
        strategy=strategy,
        stop_loss_pct=stop_loss,
        take_profit_pct=take_profit,
        position_size_pct=position_size,
    )
    return safe_jsonify(result)


@app.route("/api/strategies")
def api_strategies():
    """Get list of available backtesting strategies."""
    return jsonify(get_available_strategies())


@app.route("/api/multi-signals")
def api_multi_signals():
    symbols_param = request.args.get("symbols", "")
    category = request.args.get("category", "")

    if category:
        symbols = get_category_symbols(category)[:25]
    elif symbols_param:
        symbols = [s.strip() for s in symbols_param.split(",")]
    else:
        symbols = get_category_symbols("large_cap")[:20]

    results = []
    for symbol in symbols:
        try:
            df = fetch_market_data(symbol, period="6mo", interval="1d")
            if df is not None and not df.empty:
                df_ind = calculate_all_indicators(df)
                signals = generate_signals(df_ind)
                latest = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else latest
                
                close_price = float(latest["Close"])
                prev_price = float(prev["Close"])
                
                # Skip stocks with invalid data
                if math.isnan(close_price) or math.isnan(prev_price) or prev_price == 0:
                    continue
                    
                change_pct = ((close_price - prev_price) / prev_price) * 100

                # Determine category
                sym_base = symbol.replace(".NS", "").replace(".BO", "")
                cat = "Unknown"
                if sym_base in LARGE_CAP_STOCKS: cat = "Large Cap"
                elif sym_base in MID_CAP_STOCKS: cat = "Mid Cap"
                elif sym_base in SMALL_CAP_STOCKS: cat = "Small Cap"
                elif sym_base in PENNY_STOCKS: cat = "Penny"

                results.append({
                    "symbol": symbol,
                    "name": sym_base,
                    "price": round(close_price, 2),
                    "change_pct": round(change_pct, 2),
                    "signal": signals["overall_signal"],
                    "confidence": signals["confidence"],
                    "score": signals.get("total_score", 0),
                    "category": cat,
                })
        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    results.sort(key=lambda x: abs(x.get("score", 0)), reverse=True)
    return safe_jsonify(results)


@app.route("/api/categories")
def api_categories():
    """Get stock categories with counts."""
    return jsonify([
        {"id": "large_cap", "name": "Large Cap", "count": len(LARGE_CAP_STOCKS), "description": "Top Nifty 50 & blue-chip stocks"},
        {"id": "mid_cap", "name": "Mid Cap", "count": len(MID_CAP_STOCKS), "description": "Mid-size growth companies"},
        {"id": "small_cap", "name": "Small Cap", "count": len(SMALL_CAP_STOCKS), "description": "Smaller growth-oriented stocks"},
        {"id": "penny", "name": "Penny Stocks", "count": len(PENNY_STOCKS), "description": "Low-price speculative stocks"},
    ])


@app.route("/api/stocks-by-category")
def api_stocks_by_category():
    """Get all stocks in a category."""
    category = request.args.get("category", "large_cap")
    stocks = get_stocks_by_category(category)
    return jsonify(stocks)


@app.route("/api/intraday-tips")
def api_intraday_tips():
    """Get intraday trading tips for a single stock."""
    symbol = request.args.get("symbol", "RELIANCE.NS")
    df = fetch_market_data(symbol, period="3mo", interval="1d")
    if df is None:
        return jsonify({"action": "WAIT", "reasoning": ["No data available"]})

    tips = generate_intraday_tips(symbol, df)
    return safe_jsonify(tips)


@app.route("/api/intraday-scan")
def api_intraday_scan():
    """Scan multiple stocks for best intraday opportunities."""
    category = request.args.get("category", "large_cap")
    symbols = get_category_symbols(category)[:15]
    tips = scan_for_intraday_tips(symbols, top_n=10)
    # Send to Telegram if enabled
    try:
        category = request.args.get("category", "large_cap")
        telegram_bot.send_scan_summary(tips, category)
    except Exception:
        pass
    return safe_jsonify(tips)


# ─── TELEGRAM ENDPOINTS ───

@app.route("/api/telegram/config", methods=["GET"])
def api_telegram_config():
    """Get current Telegram configuration."""
    return jsonify(telegram_bot.get_config())


@app.route("/api/telegram/config", methods=["POST"])
def api_telegram_save_config():
    """Save Telegram bot token and chat ID."""
    data = request.get_json() or {}
    bot_token = data.get("bot_token", "")
    chat_id = data.get("chat_id", "")
    enabled = data.get("enabled", True)
    result = telegram_bot.save_config(bot_token, chat_id, enabled)
    return jsonify(result)


@app.route("/api/telegram/test", methods=["POST"])
def api_telegram_test():
    """Send a test message to Telegram."""
    success = telegram_bot.send_test_message()
    if success:
        return jsonify({"success": True, "message": "Test message sent! Check your Telegram."})
    else:
        return jsonify({"success": False, "message": "Failed to send. Check your Bot Token and Chat ID."})


@app.route("/api/telegram/send-alert", methods=["POST"])
def api_telegram_send_alert():
    """Forward a triggered alert to Telegram."""
    data = request.get_json() or {}
    telegram_bot.send_alert_notification(data)
    return jsonify({"success": True})


@app.route("/api/telegram/send-tip", methods=["POST"])
def api_telegram_send_tip():
    """Send an intraday tip to Telegram."""
    data = request.get_json() or {}
    telegram_bot.send_intraday_tip(data)
    return jsonify({"success": True})


# ─── GOLDEN PICKS & CPR ENDPOINTS ───

@app.route("/api/golden-picks")
def api_golden_picks():
    """Get today's top golden intraday picks (>85% confidence)."""
    top_n = int(request.args.get("top", 6))
    picks = get_golden_picks(top_n=top_n)
    return safe_jsonify(picks)


@app.route("/api/weekly-picks")
def api_weekly_picks():
    """Get top weekly swing trade setups (>90% confidence)."""
    top_n = int(request.args.get("top", 6))
    picks = get_weekly_picks(top_n=top_n)
    return safe_jsonify(picks)


@app.route("/api/cpr")
def api_cpr():
    """Get CPR levels for a single stock."""
    symbol = request.args.get("symbol", "RELIANCE.NS")
    df = fetch_market_data(symbol, period="1mo", interval="1d")
    if df is None or len(df) < 2:
        return jsonify({"error": "No data"})
    prev = df.iloc[-2]
    cpr = calculate_cpr(float(prev["High"]), float(prev["Low"]), float(prev["Close"]))
    cpr["symbol"] = symbol
    cpr["current_price"] = round(float(df.iloc[-1]["Close"]), 2)
    return safe_jsonify(cpr)


# ─── MARKET PULSE ENDPOINTS ───

@app.route("/api/market-pulse")
def api_market_pulse():
    """Get market pulse: India VIX + Nifty trend + overall mood."""
    pulse = get_market_pulse()
    return safe_jsonify(pulse)


@app.route("/api/analyst")
def api_analyst():
    """Get analyst recommendations for a stock."""
    symbol = request.args.get("symbol", "RELIANCE.NS")
    data = get_analyst_recommendations(symbol)
    return safe_jsonify(data or {"error": "No analyst data available"})


@app.route("/api/news")
def api_news():
    """Get news sentiment for a stock."""
    symbol = request.args.get("symbol", "RELIANCE.NS")
    data = get_news_sentiment(symbol)
    return safe_jsonify(data or {"headlines": [], "overall": 0, "label": "No data"})


# ─── PAPER TRADING ENDPOINTS ───

@app.route("/api/paper-trade/start", methods=["POST"])
def api_paper_start():
    """Start paper trading — scan and auto-place dummy trades."""
    body = request.get_json() or {}
    qty = int(body.get("quantity", 1000))
    pts = float(body.get("target_points", 2))
    top = int(body.get("top_n", 5))
    force = bool(body.get("force_restart", False))
    result = start_paper_trading(qty=qty, target_pts=pts, top_n=top, force_restart=force)
    return safe_jsonify(result)


@app.route("/api/paper-trade/status")
def api_paper_status():
    """Get current status of all paper trades with live P&L."""
    data = update_paper_trades()
    return safe_jsonify(data)


@app.route("/api/paper-trade/close", methods=["POST"])
def api_paper_close():
    """Close all active trades at current price (end of day)."""
    result = close_day()
    return safe_jsonify(result)


@app.route("/api/paper-trade/history")
def api_paper_history():
    """Get historical paper trade results."""
    return safe_jsonify(get_trade_history())


@app.route("/api/paper-trade/performance")
def api_paper_performance():
    """Get overall performance statistics."""
    return safe_jsonify(get_performance_stats())


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  TradeVision — Smart Trading Dashboard (Enhanced)")
    print("  Open http://localhost:5000 in your browser")
    print("=" * 60 + "\n")
    app.run(debug=True, port=5000)
