"""
Unit tests for the Crypto API module.
"""

# pylint: disable=wrong-import-position
import sys
import os
from unittest.mock import MagicMock
import pytest
import requests
from requests.models import Response

# FIX: Add parent directory to path so imports resolve correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the module to be tested using absolute imports
from crypto.crypto_data import (
    _clean_html,
    _format_binance,
    crypto_details,
    coin_history,
    coin_details,
    _fetch_coingecko_id,
    _get_coingecko_details,
    SYMBOL_MAP,
    ID_CACHE,
    DETAILS_CACHE,
)


# --- Setup Fixture for Caches ---
@pytest.fixture(autouse=True)
def clear_caches():
    """Clear internal caches before each test."""
    ID_CACHE.clear()
    DETAILS_CACHE.clear()


# --- Utility Tests from test_crypto_data.py ---
def test_clean_html_removes_tags():
    """Test that HTML tags are stripped from a description."""
    raw_html = "<p>This is a <b>test</b> description.</p>"
    expected = "This is a test description."
    assert _clean_html(raw_html) == expected


def test_clean_html_handles_empty_string():
    """Test that an empty string returns an empty string."""
    assert _clean_html("") == ""


def test_clean_html_handles_no_tags():
    """Test that plain text is returned unchanged."""
    plain_text = "Simple text."
    assert _clean_html(plain_text) == plain_text


def test_clean_html_handles_nested_tags():
    """Test that nested HTML tags are stripped correctly."""
    raw_html = (
        "<div><p>This is a <span>nested <b>test</b></span> description.</p></div>"
    )
    expected = "This is a nested test description."
    assert _clean_html(raw_html) == expected


def test_clean_html_handles_none():
    """Test handling of None input."""
    assert _clean_html(None) == ""


# --- Binance Formatting Test ---
def test_format_binance_sorts_and_filters():
    """Test that _format_binance correctly filters for USDT, sorts by volume, and formats output."""
    mock_data = [
        {
            "symbol": "XRPUSDT",
            "lastPrice": "0.5",
            "priceChangePercent": "1.0",
            "quoteVolume": "1000",
        },
        {
            "symbol": "BTCUSDT",
            "lastPrice": "60000",
            "priceChangePercent": "2.5",
            "quoteVolume": "5000",
        },
        {
            "symbol": "ETHUSDT",
            "lastPrice": "3000",
            "priceChangePercent": "-0.5",
            "quoteVolume": "3000",
        },
        {
            "symbol": "ADABTC",
            "lastPrice": "0.000001",
            "priceChangePercent": "0.1",
            "quoteVolume": "500",
        },
    ]

    formatted_list = _format_binance(mock_data)

    assert len(formatted_list) == 3
    assert formatted_list[0]["symbol"] == "BTC"
    assert formatted_list[1]["symbol"] == "ETH"
    assert formatted_list[2]["symbol"] == "XRP"

    assert formatted_list[0]["name"] == SYMBOL_MAP["BTC"]
    assert formatted_list[0]["price"] == pytest.approx(60000.00)
    assert formatted_list[0]["volume"] == pytest.approx(5000.00)

    # Check fallback name generation
    mock_data_unk = [
        {
            "symbol": "XYZUSDT",
            "lastPrice": "1",
            "priceChangePercent": "0",
            "quoteVolume": "10",
        }
    ]
    formatted_unk = _format_binance(mock_data_unk)
    assert formatted_unk[0]["name"] == "XYZ"


# --- API Integration Tests (Mocked) ---
def test_crypto_details_success(mocker):
    """Test crypto_details returns formatted data on successful API call."""
    mock_response = MagicMock(spec=Response)
    mock_response.json.return_value = [
        {
            "symbol": "BTCUSDT",
            "lastPrice": "60000",
            "priceChangePercent": "2.5",
            "quoteVolume": "5000",
        }
    ]
    mock_response.raise_for_status.return_value = None

    mocker.patch("requests.Session.get", return_value=mock_response)

    details = crypto_details()
    assert len(details) == 1
    assert details[0]["symbol"] == "BTC"
    assert details[0]["price"] == pytest.approx(60000.0)


def test_crypto_details_api_failure_fallback_to_mock(mocker):
    """Test crypto_details falls back to mock data on API failure."""
    mocker.patch("requests.Session.get", side_effect=requests.RequestException)

    details = crypto_details()
    assert len(details) == 2
    assert details[0]["symbol"] == "BTC"


def test_coin_history_success(mocker):
    """Test coin_history returns the closing price on success."""
    # Mock Binance klines response: [timestamp, open, high, low, close, ...]
    mock_response = MagicMock(spec=Response)
    mock_response.json.return_value = [
        [
            1672531200000,
            "100.0",
            "110.0",
            "95.0",
            "105.50",
            "...",
        ]
    ]
    mock_response.raise_for_status.return_value = None

    mocker.patch("requests.Session.get", return_value=mock_response)

    price = coin_history("ETH", "2023-01-01")
    assert price == pytest.approx(105.50)


def test_coin_history_api_failure(mocker):
    """Test coin_history returns None on API failure."""
    mocker.patch("requests.Session.get", side_effect=requests.RequestException)
    price = coin_history("ETH", "2023-01-01")
    assert price is None


def test_coin_history_json_error(mocker):
    """Test coin_history returns None on JSON/Index error (empty list)."""
    mock_response = MagicMock(spec=Response)
    mock_response.json.return_value = []
    mock_response.raise_for_status.return_value = None
    mocker.patch("requests.Session.get", return_value=mock_response)

    price = coin_history("ETH", "2023-01-01")
    assert price is None


# --- CoinGecko Fetch Tests ---
def test_fetch_coingecko_id_from_cache(mocker):
    """Test fetching ID from local cache."""
    ID_CACHE["TEST"] = "test-coin-id"
    mocker.patch("requests.Session.get")
    assert _fetch_coingecko_id("TEST") == "test-coin-id"
    mocker.patch("requests.Session.get").assert_not_called()


def test_fetch_coingecko_id_success(mocker):
    """Test successful ID fetch from API."""
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"coins": [{"id": "bitcoin", "symbol": "BTC"}]}
    mocker.patch("requests.Session.get", return_value=mock_response)

    _fetch_coingecko_id("BTC")
    assert ID_CACHE["BTC"] == "bitcoin"


def test_fetch_coingecko_id_fallback(mocker):
    """Test fallback to first result if exact symbol match isn't found."""
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "coins": [
            {"id": "first-match", "symbol": "X"},
            {"id": "second-match", "symbol": "Y"},
        ]
    }
    mocker.patch("requests.Session.get", return_value=mock_response)

    assert _fetch_coingecko_id("Z") == "first-match"


def test_fetch_coingecko_id_no_results(mocker):
    """Test empty results from API."""
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"coins": []}
    mocker.patch("requests.Session.get", return_value=mock_response)

    assert _fetch_coingecko_id("NONEXIST") is None


def test_fetch_coingecko_id_api_failure(mocker):
    """Test API failure (non-200 status)."""
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 404
    mocker.patch("requests.Session.get", return_value=mock_response)

    assert _fetch_coingecko_id("BTC") is None


def test_fetch_coingecko_id_network_error(mocker):
    """Test network error during fetch."""
    mocker.patch("requests.Session.get", side_effect=requests.RequestException)
    assert _fetch_coingecko_id("BTC") is None


# --- CoinGecko Details Tests ---
def test_get_coingecko_details_from_cache(mocker):
    """Test fetching details from local cache."""
    DETAILS_CACHE["BTC"] = {"name": "Cached Bitcoin"}
    mocker.patch("requests.Session.get")
    assert _get_coingecko_details("BTC") == {"name": "Cached Bitcoin"}
    mocker.patch("requests.Session.get").assert_not_called()


def test_get_coingecko_details_id_not_found(mocker):
    """Test when ID cannot be resolved."""
    mocker.patch("crypto.crypto_data._fetch_coingecko_id", return_value=None)
    assert _get_coingecko_details("FAIL") is None


def test_get_coingecko_details_success(mocker):
    """Test successful details fetch."""
    # PATCH: changed patch path
    mocker.patch("crypto.crypto_data._fetch_coingecko_id", return_value="test-id")
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "symbol": "BTC",
        "name": "Bitcoin",
        "description": {"en": "The original crypto."},
        "market_data": {
            "current_price": {"usd": 60000},
            "market_cap": {"usd": 1_000_000_000_000},
            "circulating_supply": 19000000,
            "ath": {"usd": 70000},
        },
    }
    mocker.patch("requests.Session.get", return_value=mock_response)

    details = _get_coingecko_details("BTC")
    assert details["description"] == "The original crypto."
    assert DETAILS_CACHE["BTC"] == details


def test_get_coingecko_details_no_description(mocker):
    """Test handling of missing description."""
    mocker.patch("crypto.crypto_data._fetch_coingecko_id", return_value="test-id")
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "symbol": "XYZ",
        "name": "Unknown Coin",
        "description": {},
        "market_data": {},
    }
    mocker.patch("requests.Session.get", return_value=mock_response)

    details = _get_coingecko_details("XYZ")
    assert "No description available" in details["description"]


def test_get_coingecko_details_api_failure(mocker):
    """Test API failure during details fetch."""
    mocker.patch("crypto.crypto_data._fetch_coingecko_id", return_value="test-id")
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 404
    mocker.patch("requests.Session.get", return_value=mock_response)

    assert _get_coingecko_details("BTC") is None


def test_get_coingecko_details_network_error(mocker):
    """Test network error during details fetch."""
    mocker.patch("crypto.crypto_data._fetch_coingecko_id", return_value="test-id")
    mocker.patch("requests.Session.get", side_effect=requests.RequestException)

    assert _get_coingecko_details("BTC") is None


# --- Final coin_details function test to cover fallback logic ---


def test_coin_details_coingecko_success(mocker):
    """Test full coin_details flow via CoinGecko."""
    # PATCH: changed patch path
    mocker.patch(
        "crypto.crypto_data._get_coingecko_details",
        return_value={"name": "CG Bitcoin", "symbol": "BTC"},
    )
    mock_binance = mocker.patch("requests.Session.get")

    result = coin_details("BTC")
    assert result["name"] == "CG Bitcoin"
    mock_binance.assert_not_called()


def test_coin_details_coingecko_failure_binance_fallback_success(mocker):
    """Test fallback to Binance when CoinGecko fails."""
    mocker.patch("crypto.crypto_data._get_coingecko_details", return_value=None)

    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 200
    # Mock Binance response for ETH (non-BTC)
    mock_response.json.return_value = {
        "symbol": "ETHUSDT",
        "lastPrice": "3000",
        "highPrice": "3500",
        "priceChangePercent": "0",
        "quoteVolume": "1",  # Minimal fields for success
    }
    mock_response.raise_for_status.return_value = None
    mocker.patch("requests.Session.get", return_value=mock_response)

    result = coin_details("ETH")
    assert result["name"] == "Ethereum"
    assert result["price"] == pytest.approx(3000.0)
    # Check non-BTC mock supply path
    assert result["supply"] == 1000000000


def test_coin_details_all_failure(mocker):
    """Test failure of both CoinGecko and Binance."""
    mocker.patch("crypto.crypto_data._get_coingecko_details", return_value=None)
    mocker.patch("requests.Session.get", side_effect=requests.RequestException)

    result = coin_details("XYZ")
    assert result["name"] == "XYZ"
    assert result["price"] == 0
    assert result["description"] == "Data unavailable."


def test_coin_details_binance_api_error_fallback(mocker):
    """Test fallback when Binance returns an HTTP error."""
    mocker.patch("crypto.crypto_data._get_coingecko_details", return_value=None)
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 400
    mock_response.raise_for_status.side_effect = requests.HTTPError
    mocker.patch("requests.Session.get", return_value=mock_response)

    result = coin_details("XYZ")
    assert result["name"] == "XYZ"
    assert result["price"] == 0
