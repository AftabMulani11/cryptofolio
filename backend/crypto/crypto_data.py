"""
Crypto Data Module.
Fetches static and historical data from CoinGecko and Binance APIs.
"""

import re
from datetime import datetime
import requests

FORCE_MOCK = False
BINANCE_URL = "https://api.binance.com/api/v3"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

# Initialize a global session for connection pooling (Keep-Alive)
session = requests.Session()

# Caches to prevent hitting API rate limits
ID_CACHE = {}  # Maps Symbol -> CoinGecko ID (e.g., 'BTC' -> 'bitcoin')
DETAILS_CACHE = {}  # Maps Symbol -> Full Data Dict

SYMBOL_MAP = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "USDT": "Tether",
    "BNB": "Binance Coin",
    "SOL": "Solana",
    "USDC": "USDC",
    "XRP": "Ripple",
    "DOGE": "Dogecoin",
    "ADA": "Cardano",
    "AVAX": "Avalanche",
    "SHIB": "Shiba Inu",
    "DOT": "Polkadot",
}


def _clean_html(raw_html):
    """Removes HTML tags from descriptions."""
    if not raw_html:
        return ""
    cleanr = re.compile("<.*?>")
    return re.sub(cleanr, "", raw_html)


def _fetch_coingecko_id(symbol):
    """Helper to resolve symbol to CoinGecko ID."""
    if symbol in ID_CACHE:
        return ID_CACHE[symbol]

    try:
        search_res = session.get(
            f"{COINGECKO_API_URL}/search?query={symbol}",
            headers={"User-Agent": "CryptoFolioApp/1.0"},
            timeout=3,
        )
        if search_res.status_code != 200:
            return None

        candidates = search_res.json().get("coins", [])
        found_id = None

        # Look for exact symbol match
        for coin in candidates:
            if coin["symbol"].upper() == symbol:
                found_id = coin["id"]
                break

        # Fallback to first result
        if not found_id and candidates:
            found_id = candidates[0]["id"]

        if found_id:
            ID_CACHE[symbol] = found_id
            return found_id

    except Exception:  # pylint: disable=broad-exception-caught
        return None
    return None


def _get_coingecko_details(symbol):
    """Fetches dynamic description and metadata from CoinGecko."""
    s_upper = symbol.upper()

    if s_upper in DETAILS_CACHE:
        return DETAILS_CACHE[s_upper]

    coin_id = _fetch_coingecko_id(s_upper)
    if not coin_id:
        return None

    try:
        url = (
            f"{COINGECKO_API_URL}/coins/{coin_id}"
            "?localization=false&tickers=false&market_data=true"
            "&community_data=false&developer_data=false&sparkline=false"
        )
        res = session.get(url, headers={"User-Agent": "CryptoFolioApp/1.0"}, timeout=3)

        if res.status_code == 200:
            data = res.json()
            description = _clean_html(data.get("description", {}).get("en", ""))
            mkt = data.get("market_data", {})

            result = {
                "symbol": data.get("symbol", symbol).upper(),
                "name": data.get("name", symbol),
                "price": mkt.get("current_price", {}).get("usd", 0),
                "market_cap": mkt.get("market_cap", {}).get("usd", 0),
                "supply": mkt.get("circulating_supply", 0),
                "ath": mkt.get("ath", {}).get("usd", 0),
                "description": (
                    description
                    if description
                    else f"No description available for {data.get('name')}."
                ),
            }
            DETAILS_CACHE[s_upper] = result
            return result

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"CoinGecko API Error for {symbol}: {e}")

    return None


def _format_binance(data):
    usdt = [i for i in data if i["symbol"].endswith("USDT")]
    sorted_data = sorted(usdt, key=lambda x: float(x["quoteVolume"]), reverse=True)[
        :500
    ]
    return [
        {
            "rank": i + 1,
            "name": SYMBOL_MAP.get(c["symbol"][:-4], c["symbol"][:-4]),
            "symbol": c["symbol"][:-4],
            "price": float(c["lastPrice"]),
            "change_24h": float(c["priceChangePercent"]),
            "volume": float(c["quoteVolume"]),
        }
        for i, c in enumerate(sorted_data)
    ]


def _generate_mock():
    return [
        {
            "rank": 1,
            "name": "Bitcoin",
            "symbol": "BTC",
            "price": 65000.00,
            "change_24h": 2.5,
            "volume": 1000000000,
        },
        {
            "rank": 2,
            "name": "Ethereum",
            "symbol": "ETH",
            "price": 3088.56,
            "change_24h": -1.2,
            "volume": 500000000,
        },
    ]


def crypto_details():
    """Fetches 24hr ticker data for top coins using a persistent session."""
    if FORCE_MOCK:
        return _generate_mock()
    try:
        res = session.get(f"{BINANCE_URL}/ticker/24hr", timeout=3)
        res.raise_for_status()
        return _format_binance(res.json())
    except (requests.RequestException, ValueError):
        return _generate_mock()


def coin_history(symbol, date_str):
    """Fetches historical price for a given date using a persistent session."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        ts = int(dt.timestamp() * 1000)
        res = session.get(
            f"{BINANCE_URL}/klines",
            params={
                "symbol": f"{symbol.upper()}USDT",
                "interval": "1d",
                "startTime": ts,
                "limit": 1,
            },
            timeout=3,
        )
        return float(res.json()[0][4])
    except (requests.RequestException, ValueError, IndexError):
        return None


def coin_details(symbol):
    """
    Fetches detailed data for a specific coin.
    PRIORITY: Tries CoinGecko first for rich description/metadata.
    FALLBACK: Uses Binance if CoinGecko fails or rate limit is hit.
    """
    s = symbol.upper()

    # 1. Try fetching rich data from CoinGecko
    cg_data = _get_coingecko_details(s)
    if cg_data:
        return cg_data

    # 2. Fallback to Binance (No description, just market data)
    try:
        res = session.get(f"{BINANCE_URL}/ticker/24hr?symbol={s}USDT", timeout=3)
        res.raise_for_status()
        data = res.json()

        current_price = float(data["lastPrice"])
        high_price = float(data["highPrice"])

        mock_supply = 19000000 if s == "BTC" else 1000000000
        market_cap = current_price * mock_supply

        return {
            "symbol": s,
            "name": SYMBOL_MAP.get(s, s),
            "price": current_price,
            "market_cap": market_cap,
            "supply": mock_supply,
            "ath": high_price * 1.5,
            "description": f"{SYMBOL_MAP.get(s, s)} is a leading cryptocurrency.",
        }
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Error fetching details for {s}: {e}")
        return {
            "symbol": s,
            "name": s,
            "price": 0,
            "market_cap": 0,
            "supply": 0,
            "ath": 0,
            "description": "Data unavailable.",
        }
