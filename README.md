# TradeVision — Smart Trading Dashboard

TradeVision is a premium trading dashboard with Technical Analysis, Backtesting Engine, Smart Alerts, and Intraday Tips for NSE/BSE stocks.

## Features

- **Dashboard:** Real-time tracking of NSE/BSE stocks.
- **Intraday Tips:** CPR-based intraday engine providing high-confidence tips, support/resistance targets, and stop-loss levels.
- **Backtester:** Test different trading strategies over historical data.
- **Watchlist:** Categorized scanning of Large Cap, Mid Cap, Small Cap, and Penny stocks.
- **Golden Picks & Weekly Strategy:** Advanced scanners for high-probability setups.
- **Telegram Alerts:** Get live intraday tips directly on your phone via Telegram.

## Prerequisites

Before running this project, ensure you have the following installed on your laptop:
- **Python 3.10 to 3.12** (Python 3.14 is currently not fully supported by some dependencies).
- **Git** (optional, but recommended for cloning the repository).

## Installation & Setup

1. **Clone the repository (or download as ZIP):**
   ```bash
   git clone https://github.com/praveenmugadur4/TradeVision.git
   cd TradeVision
   ```
   *(If your friend downloaded the ZIP, they just need to extract it and open a terminal inside the extracted folder.)*

2. **Create a virtual environment (Recommended):**
   ```bash
   python -m venv venv
   ```
   - On Windows: `venv\Scripts\activate`
   - On Mac/Linux: `source venv/bin/activate`

3. **Install the required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```
   *(You can also use `py -3 app.py` on Windows).*

5. **Open the Dashboard:**
   Open your web browser and go to: [http://localhost:5000](http://localhost:5000)

## Telegram Bot Configuration (Optional)

If you want to receive Telegram alerts:
1. Go to Telegram and message **@BotFather** to create a new bot and get your **Bot Token**.
2. Message **@userinfobot** to get your **Chat ID**.
3. In the TradeVision app, go to the **Alerts** tab, enter your Token and Chat ID, and click **Save Settings**.
