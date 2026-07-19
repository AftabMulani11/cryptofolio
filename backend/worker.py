"""
Standalone Worker Module.

This runs the WebSocket worker to collect live market data from Binance.
"""

import os
import sys
import time
import traceback

# pylint: disable=wrong-import-position
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from crypto import binance_ws

# Standard prefix for log messages to distinguish worker output
LOG_PREFIX = "worker>"


def _print(*parts):
    """
    Wrapper for print statements to enforce consistent logging formatting.
    """
    print(f"{LOG_PREFIX}", *parts)


def _start_once():
    """
    Executes a single run of the WebSocket worker.
    This function blocks until the WebSocket connection closes or crashes.
    """
    _print("Starting single run of websocket worker.")
    binance_ws.run_ws()


def _start_with_retries(max_retries=None, initial_delay=2, max_delay=60):
    """
    Runs the WebSocket worker within a retry loop to handle crashes or network instability.
    Parameters:
        max_retries (int or None): Maximum number of retry attempts. None for infinite retries.
        initial_delay (int): Initial delay in seconds before the first retry.
        max_delay (int): Maximum delay in seconds between retries.
    """
    attempt = 0
    delay = initial_delay

    while True:
        attempt += 1
        try:
            _print(f"Attempt #{attempt} — launching websocket (delay={delay}s)")

            # Start the blocking worker function
            _start_once()

            # If the worker returns normally without error, exit the loop
            _print("run_ws returned normally. Exiting retry loop.")
            break

        except KeyboardInterrupt:
            _print("Received KeyboardInterrupt — shutting down gracefully.")
            # Re-raise to allow the main block to handle exit
            raise

        except Exception as exc:  # pylint: disable=broad-exception-caught
            _print("Worker crashed with exception:", exc)
            traceback.print_exc()

            # Check if retry limit has been reached
            if max_retries is not None and attempt >= max_retries:
                _print(f"Max retries reached ({max_retries}). Giving up.")
                raise

            # Exponential backoff logic
            time.sleep(delay)
            delay = min(delay * 2, max_delay)
            _print(f"Retrying after sleeping for {delay}s (attempt {attempt + 1}).")


if __name__ == "__main__":  # pragma: no cover
    _print("🚀 Starting Standalone WebSocket Worker...")
    _print("   - Collecting live market data from Binance")
    _print("   - Syncing to 'crypto/live_data.json'")

    # Determine execution mode from environment variables
    # Modes: 'once' (single run), 'retry' (limited retries), default (infinite retries)
    env_mode = os.getenv("WORKER_MODE", "").lower()

    if env_mode == "once":
        MODE = "once"
    elif env_mode == "retry":
        MODE = "retry"
    else:
        MODE = "retry_forever"

    try:
        if MODE == "once":
            _print("Mode=once -> executing a single run now.")
            _start_once()
        elif MODE == "retry":
            _print("Mode=retry -> will try up to 5 times.")
            _start_with_retries(max_retries=5)
        else:
            _print("Mode=retry_forever -> will keep trying until killed.")
            _start_with_retries(max_retries=None)

    except KeyboardInterrupt:
        _print("\n🛑 Worker stopped by user (KeyboardInterrupt).")

    except Exception as e:  # pylint: disable=broad-exception-caught
        # Catch-all for fatal errors that bubble up from the retry logic
        _print(f"\n❌ Worker crashed fatally: {e}")
        _print(
            "See traceback above for details. Consider checking network / API keys / rate limits."
        )
        sys.exit(1)
