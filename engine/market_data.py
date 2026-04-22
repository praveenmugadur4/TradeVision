"""
Market Data Module — Fetches OHLCV data from Yahoo Finance for NSE/BSE stocks.
Enhanced with stock categorization (Large Cap, Mid Cap, Small Cap, Penny Stocks).
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import json
import time

# In-memory cache to avoid redundant API calls
_cache = {}
_cache_ttl = 300  # 5 minutes


def _get_cache_key(symbol, period, interval):
    return f"{symbol}_{period}_{interval}"


def _is_cache_valid(key):
    if key not in _cache:
        return False
    return (time.time() - _cache[key]["timestamp"]) < _cache_ttl


def normalize_symbol(symbol):
    """Ensure symbol has correct NSE/BSE suffix."""
    symbol = symbol.upper().strip()
    if not symbol.endswith(".NS") and not symbol.endswith(".BO"):
        symbol += ".NS"  # Default to NSE
    return symbol


def fetch_market_data(symbol, period="1y", interval="1d"):
    """
    Fetch OHLCV data for a given stock symbol.
    """
    symbol = normalize_symbol(symbol)
    cache_key = _get_cache_key(symbol, period, interval)

    if _is_cache_valid(cache_key):
        return _cache[cache_key]["data"]

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)

        if df.empty:
            return None

        # Clean up columns — handle MultiIndex from newer yfinance versions
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Ensure standard column names
        df.columns = [col.strip() for col in df.columns]

        # Remove timezone info for JSON serialization
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        # Cache the result
        _cache[cache_key] = {
            "data": df,
            "timestamp": time.time()
        }

        return df

    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None


def get_stock_info(symbol):
    """Get stock metadata (name, sector, market cap, etc.)."""
    symbol = normalize_symbol(symbol)
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            "symbol": symbol,
            "name": info.get("longName", info.get("shortName", symbol)),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "marketCap": info.get("marketCap", 0),
            "currentPrice": info.get("currentPrice", info.get("regularMarketPrice", 0)),
            "dayHigh": info.get("dayHigh", 0),
            "dayLow": info.get("dayLow", 0),
            "previousClose": info.get("previousClose", 0),
            "open": info.get("open", 0),
            "volume": info.get("volume", 0),
            "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh", 0),
            "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow", 0),
            "peRatio": info.get("trailingPE", 0),
            "bookValue": info.get("bookValue", 0),
            "dividendYield": info.get("dividendYield", 0),
            "currency": info.get("currency", "INR"),
        }
    except Exception as e:
        print(f"Error fetching info for {symbol}: {e}")
        return {"symbol": symbol, "name": symbol, "error": str(e)}


# ═══════════════════════════════════════════════════════
#  STOCK CATEGORIES — Large Cap, Mid Cap, Small Cap, Penny
# ═══════════════════════════════════════════════════════

LARGE_CAP_STOCKS = {
    "RELIANCE": "Reliance Industries",
    "TCS": "Tata Consultancy Services",
    "HDFCBANK": "HDFC Bank",
    "INFY": "Infosys",
    "ICICIBANK": "ICICI Bank",
    "HINDUNILVR": "Hindustan Unilever",
    "SBIN": "State Bank of India",
    "BHARTIARTL": "Bharti Airtel",
    "ITC": "ITC Limited",
    "KOTAKBANK": "Kotak Mahindra Bank",
    "LT": "Larsen & Toubro",
    "AXISBANK": "Axis Bank",
    "WIPRO": "Wipro",
    "ASIANPAINT": "Asian Paints",
    "MARUTI": "Maruti Suzuki",
    "TITAN": "Titan Company",
    "SUNPHARMA": "Sun Pharma",
    "ULTRACEMCO": "UltraTech Cement",
    "BAJFINANCE": "Bajaj Finance",
    "HCLTECH": "HCL Technologies",
    "NESTLEIND": "Nestle India",
    "TATAMOTORS": "Tata Motors",
    "TATASTEEL": "Tata Steel",
    "POWERGRID": "Power Grid Corp",
    "NTPC": "NTPC Limited",
    "ONGC": "Oil & Natural Gas Corp",
    "JSWSTEEL": "JSW Steel",
    "ADANIENT": "Adani Enterprises",
    "ADANIPORTS": "Adani Ports",
    "TECHM": "Tech Mahindra",
    "DRREDDY": "Dr. Reddy's Labs",
    "CIPLA": "Cipla",
    "COALINDIA": "Coal India",
    "BPCL": "Bharat Petroleum",
    "GRASIM": "Grasim Industries",
    "BAJAJFINSV": "Bajaj Finserv",
    "DIVISLAB": "Divi's Laboratories",
    "EICHERMOT": "Eicher Motors",
    "HEROMOTOCO": "Hero MotoCorp",
    "APOLLOHOSP": "Apollo Hospitals",
    "BRITANNIA": "Britannia Industries",
    "INDUSINDBK": "IndusInd Bank",
    "TATACONSUM": "Tata Consumer Products",
    "HDFCLIFE": "HDFC Life Insurance",
    "SBILIFE": "SBI Life Insurance",
    "BAJAJ-AUTO": "Bajaj Auto",
    "VEDL": "Vedanta Limited",
    "ZOMATO": "Zomato",
    "M&M": "Mahindra & Mahindra",
    "HINDALCO": "Hindalco Industries",
}

MID_CAP_STOCKS = {
    "TRENT": "Trent Limited",
    "GODREJCP": "Godrej Consumer Products",
    "PIDILITIND": "Pidilite Industries",
    "HAVELLS": "Havells India",
    "MCDOWELL-N": "United Spirits",
    "VOLTAS": "Voltas Limited",
    "POLYCAB": "Polycab India",
    "PERSISTENT": "Persistent Systems",
    "COFORGE": "Coforge Limited",
    "MPHASIS": "Mphasis",
    "LTIM": "LTIMindtree",
    "DALBHARAT": "Dalmia Bharat",
    "IDFCFIRSTB": "IDFC First Bank",
    "FEDERALBNK": "Federal Bank",
    "BANDHANBNK": "Bandhan Bank",
    "PNB": "Punjab National Bank",
    "BANKBARODA": "Bank of Baroda",
    "CANBK": "Canara Bank",
    "MFSL": "Max Financial Services",
    "NAUKRI": "Info Edge (Naukri)",
    "PHOENIXLTD": "Phoenix Mills",
    "OBEROIRLTY": "Oberoi Realty",
    "PRESTIGE": "Prestige Estates",
    "GODREJPROP": "Godrej Properties",
    "ESCORTS": "Escorts Kubota",
    "MRF": "MRF Limited",
    "TORNTPHARM": "Torrent Pharma",
    "AUROPHARMA": "Aurobindo Pharma",
    "LUPIN": "Lupin Limited",
    "BIOCON": "Biocon Limited",
    "PAGEIND": "Page Industries",
    "TATAPOWER": "Tata Power Company",
    "ADANIGREEN": "Adani Green Energy",
    "NHPC": "NHPC Limited",
    "IRCTC": "IRCTC",
    "HAL": "Hindustan Aeronautics",
    "BEL": "Bharat Electronics",
    "PIIND": "PI Industries",
    "ASTRAL": "Astral Limited",
    "CROMPTON": "Crompton Greaves CE",
}

SMALL_CAP_STOCKS = {
    "RBLBANK": "RBL Bank",
    "MANAPPURAM": "Manappuram Finance",
    "L&TFH": "L&T Finance",
    "UJJIVANSFB": "Ujjivan SFB",
    "EQUITASBNK": "Equitas SFB",
    "KALYANKJIL": "Kalyan Jewellers",
    "PCJEWELLER": "PC Jeweller",
    "ROUTE": "Route Mobile",
    "HAPPSTMNDS": "Happiest Minds",
    "KPITTECH": "KPIT Technologies",
    "TATAELXSI": "Tata Elxsi",
    "ZENTEC": "Zensar Technologies",
    "STARHEALTH": "Star Health Insurance",
    "NIACL": "New India Assurance",
    "RVNL": "Rail Vikas Nigam",
    "IRFC": "Indian Railway Finance",
    "HUDCO": "HUDCO",
    "RECLTD": "REC Limited",
    "PFC": "Power Finance Corp",
    "SJVN": "SJVN Limited",
    "JSWENERGY": "JSW Energy",
    "CESC": "CESC Limited",
    "GAIL": "GAIL India",
    "PETRONET": "Petronet LNG",
    "IGL": "Indraprastha Gas",
    "MARICO": "Marico Limited",
    "EMAMILTD": "Emami Limited",
    "BATAINDIA": "Bata India",
    "RELAXO": "Relaxo Footwears",
    "VMART": "V-Mart Retail",
    "ZYDUSLIFE": "Zydus Lifesciences",
    "IPCALAB": "IPCA Laboratories",
    "GRANULES": "Granules India",
    "NATCOPHARM": "Natco Pharma",
    "LAURUS": "Laurus Labs",
    "DEEPAKNTR": "Deepak Nitrite",
    "AARTI": "Aarti Industries",
    "CLEAN": "Clean Science & Tech",
    "SWSOLAR": "Sterling & Wilson Solar",
    "CANFINHOME": "Can Fin Homes",
}

PENNY_STOCKS = {
    "SUZLON": "Suzlon Energy",
    "YESBANK": "Yes Bank",
    "IDEA": "Vodafone Idea",
    "JPPOWER": "Jaiprakash Power",
    "JPASSOCIAT": "Jaypee Infratech",
    "RPOWER": "Reliance Power",
    "RCOM": "Reliance Communications",
    "GTLINFRA": "GTL Infrastructure",
    "UNITECH": "Unitech Limited",
    "DHFL": "DHFL",
    "HFCL": "HFCL Limited",
    "BHEL": "Bharat Heavy Electricals",
    "SAIL": "Steel Authority of India",
    "NATIONALUM": "National Aluminium",
    "HINDCOPPER": "Hindustan Copper",
    "NMDC": "NMDC Limited",
    "NBCC": "NBCC India",
    "IRCON": "IRCON International",
    "ENGINERSIN": "Engineers India",
    "NHPC": "NHPC Limited",
    "TTML": "Tata Teleservices",
    "ORIENTELEC": "Orient Electric",
    "GRINFRA": "G R Infraprojects",
    "KEC": "KEC International",
    "IOLCP": "IOL Chemicals",
    "TRIDENT": "Trident Limited",
    "GRAPHITE": "Graphite India",
    "RAIN": "Rain Industries",
    "INFIBEAM": "Infibeam Avenues",
    "QUESS": "Quess Corp",
}

ALL_STOCKS = {}
ALL_STOCKS.update(LARGE_CAP_STOCKS)
ALL_STOCKS.update(MID_CAP_STOCKS)
ALL_STOCKS.update(SMALL_CAP_STOCKS)
ALL_STOCKS.update(PENNY_STOCKS)


def get_stocks_by_category(category="all"):
    """Get stocks filtered by category."""
    categories = {
        "large_cap": LARGE_CAP_STOCKS,
        "mid_cap": MID_CAP_STOCKS,
        "small_cap": SMALL_CAP_STOCKS,
        "penny": PENNY_STOCKS,
        "all": ALL_STOCKS,
    }
    stocks = categories.get(category, ALL_STOCKS)
    return [{"symbol": f"{k}.NS", "name": v, "category": category} for k, v in stocks.items()]


def get_category_symbols(category):
    """Get symbol list for a category (for watchlist scanning)."""
    categories = {
        "large_cap": LARGE_CAP_STOCKS,
        "mid_cap": MID_CAP_STOCKS,
        "small_cap": SMALL_CAP_STOCKS,
        "penny": PENNY_STOCKS,
    }
    stocks = categories.get(category, LARGE_CAP_STOCKS)
    return [f"{k}.NS" for k in stocks.keys()]


def search_stocks(query):
    """Search for stock symbols matching a query."""
    query = query.upper().strip()
    results = []

    for symbol, name in ALL_STOCKS.items():
        if query in symbol or query.lower() in name.lower():
            # Determine category
            cat = "unknown"
            if symbol in LARGE_CAP_STOCKS:
                cat = "Large Cap"
            elif symbol in MID_CAP_STOCKS:
                cat = "Mid Cap"
            elif symbol in SMALL_CAP_STOCKS:
                cat = "Small Cap"
            elif symbol in PENNY_STOCKS:
                cat = "Penny"

            results.append({
                "symbol": f"{symbol}.NS",
                "name": name,
                "exchange": "NSE",
                "category": cat,
            })

    return results[:20]


def dataframe_to_json(df):
    """Convert DataFrame to JSON-serializable format for the frontend."""
    if df is None or df.empty:
        return []

    records = []
    for idx, row in df.iterrows():
        record = {
            "time": idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx),
            "timestamp": int(idx.timestamp()) if hasattr(idx, "timestamp") else 0,
            "open": round(float(row.get("Open", 0)), 2),
            "high": round(float(row.get("High", 0)), 2),
            "low": round(float(row.get("Low", 0)), 2),
            "close": round(float(row.get("Close", 0)), 2),
            "volume": int(row.get("Volume", 0)),
        }
        records.append(record)

    return records
