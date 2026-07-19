"""
Binance WebSocket Module.
Connects to Binance stream and saves data to a local file for IPC.
"""

import json
import logging
import threading
import time
import os
import websocket

# DATA_FILE path for IPC (Inter-Process Communication)
DATA_FILE = os.path.join(os.path.dirname(__file__), "live_data.json")

logging.basicConfig(level=logging.INFO)

# In-memory cache for the worker
latest_data = {}
data_lock = threading.Lock()


def save_data_to_file():  # pragma: no cover
    """Periodically saves data to disk for the main app to read."""
    while True:
        try:
            with data_lock:
                temp_file = DATA_FILE + ".tmp"
                # Added encoding='utf-8'
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(latest_data, f)
                os.replace(temp_file, DATA_FILE)
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Log error but keep thread alive
            logging.error("Error saving data: %s", e)
        time.sleep(1)


def on_message(_ws, message):  # pragma: no cover
    """Callback for incoming WebSocket messages."""
    try:
        data = json.loads(message)
        if isinstance(data, list):
            with data_lock:
                for ticker in data:
                    symbol = ticker["s"]
                    if not symbol.endswith("USDT"):
                        continue

                    key = symbol.lower()
                    latest_data[key] = {
                        "symbol": symbol,
                        "close": float(ticker["c"]),
                        "change": float(ticker["P"]),
                        "high": float(ticker["h"]),
                        "low": float(ticker["l"]),
                        "volume": float(ticker["q"]),
                    }
    except Exception as e:  # pylint: disable=broad-exception-caught
        logging.error("WS Parse Error: %s", e)


def on_error(_ws, error):  # pragma: no cover
    """Callback for WebSocket errors."""
    logging.error("WS Error: %s", error)


def on_close(_ws, *_args):  # pragma: no cover
    """Callback for WebSocket closure."""
    logging.info("WebSocket Closed. Reconnecting in 5s...")
    time.sleep(5)


def on_open(_ws):  # pragma: no cover
    """Callback for WebSocket connection success."""
    logging.info("WebSocket Connected (All Markets)")


def run_ws():  # pragma: no cover
    """Starts the WebSocket client."""
    saver_thread = threading.Thread(target=save_data_to_file, daemon=True)
    saver_thread.start()

    ws_url = "wss://stream.binance.com:9443/ws/!ticker@arr"
    while True:
        try:
            ws = websocket.WebSocketApp(
                ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
            )
            ws.run_forever(ping_interval=30, ping_timeout=10)
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Critical worker loop, must not crash
            logging.error("WS Connection Failed: %s", e)
            time.sleep(5)


def get_latest_data():
    """Reads the latest market data from the JSON file."""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:  # pylint: disable=broad-exception-caught
        # File read race condition expected, return empty dict
        pass
    return {}


if __name__ == "__main__":  # pragma: no cover
    print("Starting Standalone WebSocket Worker...")
    run_ws()
