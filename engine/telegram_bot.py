"""
TradeVision — Telegram Alert Bot
Sends trading alerts, intraday tips, and signal notifications to Telegram.

Setup:
1. Message @BotFather on Telegram → /newbot → save the TOKEN
2. Message @userinfobot → get your CHAT_ID
3. Set them via the dashboard Settings or environment variables
"""

import asyncio
import os
import json
import threading
from datetime import datetime

try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️  python-telegram-bot not installed. Run: pip install python-telegram-bot")


# Config file path
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "telegram_config.json")


def _load_config():
    """Load Telegram config from file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"bot_token": "", "chat_id": "", "enabled": False}


def _save_config(config):
    """Save Telegram config to file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_config():
    """Get current Telegram configuration (safe for API response)."""
    config = _load_config()
    return {
        "enabled": config.get("enabled", False),
        "chat_id": config.get("chat_id", ""),
        "bot_token_set": bool(config.get("bot_token", "")),
    }


def save_config(bot_token, chat_id, enabled=True):
    """Save Telegram bot token and chat ID."""
    config = {
        "bot_token": bot_token,
        "chat_id": str(chat_id),
        "enabled": enabled,
    }
    _save_config(config)
    return {"success": True, "message": "Telegram configuration saved"}


def _send_message_sync(text, parse_mode="HTML"):
    """Send a Telegram message (synchronous wrapper)."""
    if not TELEGRAM_AVAILABLE:
        print("⚠️ Telegram not available")
        return False

    config = _load_config()
    if not config.get("enabled") or not config.get("bot_token") or not config.get("chat_id"):
        return False

    try:
        async def _send():
            bot = Bot(token=config["bot_token"])
            await bot.send_message(
                chat_id=config["chat_id"],
                text=text,
                parse_mode=parse_mode,
            )

        # Run in a new event loop (safe for Flask's sync context)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_send())
        loop.close()
        return True
    except TelegramError as e:
        print(f"Telegram error: {e}")
        return False
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False


def send_message_async(text, parse_mode="HTML"):
    """Send a Telegram message in a background thread (non-blocking)."""
    thread = threading.Thread(target=_send_message_sync, args=(text, parse_mode))
    thread.daemon = True
    thread.start()


def send_test_message():
    """Send a test message to verify the configuration."""
    text = (
        "🟢 <b>TradeVision Connected!</b>\n\n"
        "✅ Your Telegram alerts are now active.\n"
        f"📅 {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n\n"
        "You'll receive:\n"
        "• 🎯 Trading signal alerts\n"
        "• ⚡ Intraday buy/sell tips\n"
        "• 🔔 Price trigger notifications\n\n"
        "Happy Trading! 📈"
    )
    return _send_message_sync(text)


def send_alert_notification(alert_data):
    """Send a triggered alert via Telegram."""
    symbol = alert_data.get("symbol", "")
    alert_type = alert_data.get("type", "")
    price = alert_data.get("price", "N/A")

    type_labels = {
        "price_above": "📈 Price Above Target",
        "price_below": "📉 Price Below Target",
        "signal_buy": "🟢 Buy Signal Generated",
        "signal_sell": "🔴 Sell Signal Generated",
        "rsi_oversold": "📊 RSI Oversold (< 30)",
        "rsi_overbought": "📊 RSI Overbought (> 70)",
    }

    label = type_labels.get(alert_type, alert_type)
    text = (
        f"🔔 <b>ALERT TRIGGERED</b>\n\n"
        f"📌 <b>{symbol}</b>\n"
        f"📋 {label}\n"
        f"💰 Current Price: ₹{price}\n"
        f"🕐 {datetime.now().strftime('%I:%M %p, %d %b %Y')}"
    )
    send_message_async(text)


def send_signal_update(symbol, signal, confidence, price):
    """Send a trading signal update."""
    signal_emoji = {
        "STRONG_BUY": "🟢🟢",
        "BUY": "🟢",
        "HOLD": "🟡",
        "SELL": "🔴",
        "STRONG_SELL": "🔴🔴",
    }
    emoji = signal_emoji.get(signal, "⚪")

    text = (
        f"{emoji} <b>Signal Update: {symbol}</b>\n\n"
        f"📊 Signal: <b>{signal.replace('_', ' ')}</b>\n"
        f"🎯 Confidence: {confidence}%\n"
        f"💰 Price: ₹{price}\n"
        f"🕐 {datetime.now().strftime('%I:%M %p')}"
    )
    send_message_async(text)


def send_intraday_tip(tip):
    """Send an intraday trading tip."""
    action = tip.get("action", "WAIT")
    symbol = tip.get("symbol", "").replace(".NS", "")

    action_emoji = {"BUY": "🟢", "SELL": "🔴", "WAIT": "🟡"}
    emoji = action_emoji.get(action, "⚪")

    text = f"{emoji} <b>INTRADAY TIP: {action}</b>\n\n"
    text += f"📌 <b>{symbol}</b>\n"
    text += f"💰 CMP: ₹{tip.get('current_price', 'N/A')}\n"

    if action != "WAIT":
        text += f"🎯 Entry: ₹{tip.get('entry_price', 'N/A')}\n"
        text += f"✅ Target: ₹{tip.get('target', 'N/A')}\n"
        text += f"🛑 Stop Loss: ₹{tip.get('stop_loss', 'N/A')}\n"
        text += f"⚖️ Risk:Reward = 1:{tip.get('risk_reward', 'N/A')}\n"

    text += f"📈 Confidence: {tip.get('confidence', 0)}%\n\n"

    # Add reasoning
    reasoning = tip.get("reasoning", [])
    if reasoning:
        text += "<b>Analysis:</b>\n"
        for r in reasoning[:5]:
            text += f"• {r}\n"

    text += f"\n🕐 {datetime.now().strftime('%I:%M %p, %d %b %Y')}"
    send_message_async(text)


def send_scan_summary(tips, category=""):
    """Send a summary of intraday scan results."""
    buy_tips = [t for t in tips if t.get("action") == "BUY"]
    sell_tips = [t for t in tips if t.get("action") == "SELL"]

    text = f"📊 <b>INTRADAY SCAN RESULTS</b>\n"
    if category:
        text += f"📁 Category: {category.replace('_', ' ').title()}\n"
    text += f"🕐 {datetime.now().strftime('%I:%M %p, %d %b %Y')}\n\n"

    if buy_tips:
        text += f"🟢 <b>BUY Opportunities ({len(buy_tips)})</b>\n"
        for tip in buy_tips[:5]:
            sym = tip.get("symbol", "").replace(".NS", "")
            text += f"  • {sym} — ₹{tip.get('current_price', '?')} → Target ₹{tip.get('target', '?')} (Conf: {tip.get('confidence', 0)}%)\n"
        text += "\n"

    if sell_tips:
        text += f"🔴 <b>SELL Signals ({len(sell_tips)})</b>\n"
        for tip in sell_tips[:5]:
            sym = tip.get("symbol", "").replace(".NS", "")
            text += f"  • {sym} — ₹{tip.get('current_price', '?')} → Target ₹{tip.get('target', '?')} (Conf: {tip.get('confidence', 0)}%)\n"
        text += "\n"

    if not buy_tips and not sell_tips:
        text += "🟡 No strong signals found. Market may be sideways.\n"

    text += f"\n📈 Total Stocks Scanned: {len(tips)}"
    send_message_async(text)
