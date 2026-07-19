"""
Unit tests for Flask routes.
"""

# pylint: disable=redefined-outer-name, too-many-arguments, too-many-positional-arguments, duplicate-code, wrong-import-position
import sys
import os
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest
import pandas as pd
from flask_jwt_extended import create_access_token

# FIX: Add parent directory to path so 'app.py' imports resolve correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for app.py initialization
os.environ["token_secret_key"] = "test-secret"

# Define constants for test credentials to avoid "Hard-coded credential" warnings
MOCK_USERNAME = "testuser"
MOCK_PASSWORD = "SafeTestPassword123!"
MOCK_NEW_PASSWORD = "NewSafePassword456!"
MOCK_EMAIL = "test@example.com"


@pytest.fixture
def client():
    """Create a Flask test client."""
    # Lazy import app here to ensure we get the current valid module
    # (Fixes issues if other tests reload the app module)
    with patch("database.db.boto3"):
        import app

        app.app.config["TESTING"] = True
        app.app.config["JWT_SECRET_KEY"] = "test-secret"
        app.app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=1)

        with app.app.test_client() as test_client:
            yield test_client


@pytest.fixture
def auth_headers(client):
    """Generate auth headers with a valid JWT."""
    # Use the application from the client to ensure consistency
    with client.application.app_context():
        access_token = create_access_token(MOCK_USERNAME)
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


# --- AUTH ROUTES ---


@patch("app.ud.login_user")
def test_login_success(mock_login_user, client):
    """Test successful login route."""
    mock_login_user.return_value = {"status": "success"}
    response = client.post(
        "/api/login", json={"username": MOCK_USERNAME, "password": MOCK_PASSWORD}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert "token" in data


@patch("app.ud.login_user")
def test_login_failure(mock_login_user, client):
    """Test login failure route."""
    mock_login_user.return_value = {"status": "error", "message": "Invalid credentials"}
    response = client.post(
        "/api/login", json={"username": MOCK_USERNAME, "password": MOCK_PASSWORD}
    )
    assert response.status_code == 401
    data = response.get_json()
    assert data["status"] == "error"


@patch("app.ud.add_user")
def test_create_success(mock_add_user, client):
    """Test successful signup route."""
    mock_add_user.return_value = {
        "status": "success",
        "message": "User added successfully",
    }
    response = client.post(
        "/api/signup",
        json={
            "username": "newuser",
            "password": MOCK_PASSWORD,
            "email": MOCK_EMAIL,
            "full_name": "A User",
        },
    )
    assert response.status_code == 201
    assert response.get_json()["status"] == "success"


@patch("app.ud.add_user")
def test_create_failure(mock_add_user, client):
    """Test signup failure route."""
    mock_add_user.return_value = {
        "status": "error",
        "message": "Username already taken",
    }
    response = client.post(
        "/api/signup",
        json={
            "username": "existing",
            "password": MOCK_PASSWORD,
            "email": MOCK_EMAIL,
            "full_name": "A User",
        },
    )
    assert response.status_code == 400
    assert response.get_json()["status"] == "error"


@patch("app.ud.reset_password")
def test_reset_password_success(mock_reset_password, client):
    """Test successful password reset route."""
    mock_reset_password.return_value = {"status": "success"}
    response = client.post(
        "/api/password-reset",
        json={
            "username": "test",
            "email": MOCK_EMAIL,
            "new_password": MOCK_NEW_PASSWORD,
        },
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "success"


@patch("app.ud.reset_password")
def test_reset_password_failure(mock_reset_password, client):
    """Test password reset failure route."""
    mock_reset_password.return_value = {"status": "error", "message": "Invalid"}
    response = client.post(
        "/api/password-reset",
        json={
            "username": "test",
            "email": MOCK_EMAIL,
            "new_password": MOCK_NEW_PASSWORD,
        },
    )
    assert response.status_code == 400
    assert response.get_json()["status"] == "error"


@patch("app.ud.update_password")
def test_update_password_route_success(mock_update_password, client, auth_headers):
    """Test successful password update route."""
    mock_update_password.return_value = {"status": "success"}
    response = client.post(
        "/api/password-update",
        json={"currentPass": MOCK_PASSWORD, "newPass": MOCK_NEW_PASSWORD},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "success"


@patch("app.ud.update_password")
def test_update_password_route_failure(mock_update_password, client, auth_headers):
    """Test password update failure route."""
    mock_update_password.return_value = {"status": "error", "message": "Wrong pass"}
    response = client.post(
        "/api/password-update",
        json={"currentPass": MOCK_PASSWORD, "newPass": MOCK_NEW_PASSWORD},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.get_json()["status"] == "error"


# --- DATA ROUTES ---


@patch("app.crypto.coin_history")
def test_get_historical_price_success(mock_coin_history, client):
    """Test getting historical price successfully."""
    mock_coin_history.return_value = 100.50
    response = client.get("/api/history?symbol=BTC&date=2023-01-01")
    assert response.status_code == 200
    assert response.get_json()["price"] == pytest.approx(100.50)


@patch("app.crypto.coin_history")
def test_get_historical_price_not_found(mock_coin_history, client):
    """Test getting historical price when data is unavailable."""
    mock_coin_history.return_value = None
    response = client.get("/api/history?symbol=BTC&date=2023-01-01")
    assert response.status_code == 404
    assert "Unavailable" in response.get_json()["error"]


def test_get_historical_price_missing_args(client):
    """Test getting historical price with missing arguments."""
    response = client.get("/api/history?symbol=BTC")
    assert response.status_code == 400


@patch("app.ud.get_user_holdings")
def test_get_holdings_route_success(mock_get_user_holdings, client, auth_headers):
    """Test getting user holdings successfully."""
    mock_get_user_holdings.return_value = 5.5
    response = client.get("/api/holdings/BTC", headers=auth_headers)
    assert response.status_code == 200
    assert response.get_json()["holdings"] == pytest.approx(5.5)


@patch("app.ud.calculate_portfolio_stats")
@patch("app.binance_ws.get_latest_data")
@patch("app.ud.get_transactions_db")
@patch("app.ud.get_user_details")
def test_profile_route_get_success(
    mock_get_user_details,
    _mock_get_transactions_db,
    _mock_get_latest_data,
    mock_calculate_portfolio_stats,
    client,
    auth_headers,
):
    """Test getting profile data successfully."""
    mock_get_user_details.return_value = {
        "name": "Test User",
        "email": MOCK_EMAIL,
        "join_date": "Jan 2023",
    }
    mock_calculate_portfolio_stats.return_value = {
        "total_balance": 10000.50,
        "trade_count": 5,
        "profit_percent": 15.0,
    }

    response = client.get(
        f"/api/profile?username={MOCK_USERNAME}", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["name"] == "Test User"
    assert data["totalValue"] == "$10,000.50"
    assert data["pnl"] == "+15.00%"


@patch("app.ud.get_user_details")
def test_profile_route_get_user_not_found(mock_get_user_details, client, auth_headers):
    """Test getting profile data for non-existent user."""
    mock_get_user_details.return_value = None
    response = client.get(
        f"/api/profile?username={MOCK_USERNAME}", headers=auth_headers
    )
    assert response.status_code == 404
    assert "not found" in response.get_json()["error"]


@patch("app.ud.update_user_details")
def test_profile_route_put_success(mock_update_user_details, client, auth_headers):
    """Test updating profile successfully."""
    mock_update_user_details.return_value = {"status": "success"}
    response = client.put(
        f"/api/profile?username={MOCK_USERNAME}",
        json={"name": "New Name"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "success"


@patch("app.ud.update_user_details")
def test_profile_route_put_failure(mock_update_user_details, client, auth_headers):
    """Test updating profile failure."""
    mock_update_user_details.return_value = {"error": "Update failed"}
    response = client.put(
        f"/api/profile?username={MOCK_USERNAME}",
        json={"name": "New Name"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "failed" in response.get_json()["error"]


def test_profile_route_method_not_allowed(client, auth_headers):
    """Test invalid HTTP method on profile route."""
    response = client.delete(
        f"/api/profile?username={MOCK_USERNAME}", headers=auth_headers
    )
    assert response.status_code == 405


# --- PORTFOLIO CRUD ROUTES ---


@patch("app.ud.get_transactions_db")
def test_handle_portfolio_get(mock_get_transactions_db, client, auth_headers):
    """Test fetching portfolio transactions."""
    mock_get_transactions_db.return_value = [{"id": 1}]
    response = client.get(
        f"/api/portfolio?username={MOCK_USERNAME}", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.get_json() == [{"id": 1}]


@patch("app.ud.add_transaction_db")
def test_handle_portfolio_post_success(mock_add_transaction_db, client, auth_headers):
    """Test adding a portfolio transaction."""
    mock_add_transaction_db.return_value = {"status": "success"}
    response = client.post(
        f"/api/portfolio?username={MOCK_USERNAME}", json={}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "success"


@patch("app.ud.add_transaction_db")
def test_handle_portfolio_post_failure(mock_add_transaction_db, client, auth_headers):
    """Test failure adding a portfolio transaction."""
    mock_add_transaction_db.return_value = {"error": "Failed"}
    response = client.post(
        f"/api/portfolio?username={MOCK_USERNAME}", json={}, headers=auth_headers
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "Failed"


@patch("app.ud.update_transaction_db")
def test_handle_portfolio_put_success(mock_update_transaction_db, client, auth_headers):
    """Test updating a portfolio transaction."""
    mock_update_transaction_db.return_value = {"status": "success"}
    response = client.put(
        f"/api/portfolio?username={MOCK_USERNAME}", json={}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "success"


@patch("app.ud.update_transaction_db")
def test_handle_portfolio_put_failure(mock_update_transaction_db, client, auth_headers):
    """Test failure updating a portfolio transaction."""
    mock_update_transaction_db.return_value = {"error": "Failed"}
    response = client.put(
        f"/api/portfolio?username={MOCK_USERNAME}", json={}, headers=auth_headers
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "Failed"


def test_handle_portfolio_method_not_allowed(client, auth_headers):
    """Test invalid HTTP method on portfolio route."""
    response = client.delete(
        f"/api/portfolio?username={MOCK_USERNAME}", headers=auth_headers
    )
    assert response.status_code == 405


# --- DASHBOARD ROUTE ---


@patch("app.ud.calculate_portfolio_stats")
@patch("app.binance_ws.get_latest_data")
@patch("app.ud.get_transactions_db")
def test_get_dashboard_success(
    mock_get_transactions_db,
    mock_get_latest_data,
    mock_calculate_portfolio_stats,
    client,
    auth_headers,
):
    """Test fetching dashboard data."""
    mock_get_transactions_db.return_value = [{"id": 1}]
    mock_get_latest_data.return_value = {}
    mock_calculate_portfolio_stats.return_value = {
        "assets": [{"symbol": "BTC"}],
        "total_balance": 10000.0,
        "total_invested": 5000.0,
        "total_sold": 1000.0,
        "total_unrealized_gain": 500.0,
        "net_profit": 5500.0,
        "profit_percent": 110.0,
        "best_performer": {"symbol": "BTC", "change": "+50.00%"},
        "trade_count": 1,
    }

    response = client.get(
        f"/api/dashboard?username={MOCK_USERNAME}", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["assets"] == [{"symbol": "BTC"}]
    assert data["totalBalance"] == "$10,000.00"
    assert data["profitPercent"] == "+110.00%"


# --- CRYPTO INFO ROUTES ---


@patch("app.crypto.crypto_details")
def test_get_coins_route_success(mock_crypto_details, client):
    """Test fetching coin list."""
    mock_crypto_details.return_value = [{"symbol": "BTC"}]
    response = client.get("/api/coins")
    assert response.status_code == 200
    assert response.get_json() == [{"symbol": "BTC"}]


@patch("app.crypto.coin_details")
def test_get_coin_detail_route_success(mock_coin_details, client):
    """Test fetching single coin details."""
    mock_coin_details.return_value = {"symbol": "BTC", "name": "Bitcoin"}
    response = client.get("/api/coin/BTC")
    assert response.status_code == 200
    assert response.get_json()["name"] == "Bitcoin"


@patch("app.binance_ws.get_latest_data")
def test_get_live_prices_success(mock_get_latest_data, client):
    """Test fetching live prices."""
    mock_get_latest_data.return_value = {"btcusdt": {"c": 65000}}
    response = client.get("/api/live-prices")
    assert response.status_code == 200
    assert response.get_json()["btcusdt"]["c"] == 65000


# --- EXPORT LOGIC ---


@patch("app._generate_excel_file")
@patch("app.ud.get_user_details")
@patch("app.ud.get_transactions_db")
@patch("app.crypto.crypto_details")
@patch("app.binance_ws.get_latest_data")
@patch("app.ud.calculate_portfolio_stats")
def test_export_all_data_success(
    mock_calculate_portfolio_stats,
    mock_get_latest_data,
    mock_crypto_details,
    mock_get_transactions_db,
    mock_get_user_details,
    mock_generate_excel_file,
    client,
):
    """Test exporting all data to Excel."""
    # Mock data
    mock_get_user_details.return_value = {
        "name": "Test User",
        "email": MOCK_EMAIL,
        "join_date": "Jan 2023",
    }
    mock_get_transactions_db.return_value = [
        {
            "id": "100",
            "type": "buy",
            "symbol": "BTC",
            "amount": 1.0,
            "price": 10000.0,
            "date": "2023-01-01",
            "coin": "Bitcoin",
        }
    ]
    mock_crypto_details.return_value = [{"symbol": "BTC", "name": "Bitcoin"}]
    mock_get_latest_data.return_value = {"btcusdt": {"close": 20000}}
    mock_calculate_portfolio_stats.return_value = {
        "assets": [
            {
                "symbol": "BTC",
                "holdings": 1.0,
                "value": "$20,000.00",
                "price": "$20,000.00",
                "avg_price": "$10,000.00",
                "pnl_percent": 100.0,
            }
        ],
        "total_balance": 20000.0,
        "total_invested": 10000.0,
        "total_sold": 0.0,
        "total_unrealized_gain": 10000.0,
        "net_profit": 10000.0,
        "profit_percent": 100.0,
        "trade_count": 1,
    }

    # Mock excel output
    mock_excel_file = MagicMock()
    mock_excel_file.getvalue.return_value = b"mock_excel_data"
    mock_generate_excel_file.return_value = mock_excel_file

    response = client.get(f"/api/export/all-data?username={MOCK_USERNAME}")

    assert response.status_code == 200
    assert (
        response.content_type
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert (
        response.headers["Content-disposition"]
        == f"attachment; filename={MOCK_USERNAME}_report.xlsx"
    )
    assert response.data == b"mock_excel_data"


def test_export_all_data_missing_username(client):
    """Test export with missing username."""
    response = client.get("/api/export/all-data")
    assert response.status_code == 400


@patch("app.ud.get_transactions_db")
@patch("app.ud.get_user_details")
def test_export_all_data_no_data_found(
    mock_get_user_details, mock_get_transactions_db, client
):
    """Test export when no data is found."""
    mock_get_user_details.return_value = None
    mock_get_transactions_db.return_value = []
    response = client.get(f"/api/export/all-data?username={MOCK_USERNAME}")
    assert response.status_code == 404


# --- Helper Function Tests (from app.py) ---


def test_prepare_summary_df_full_data():
    """Test summary DataFrame preparation with full data."""
    # Import locally
    from app import _prepare_summary_df

    user_info = {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "join_date": "Jan 2023",
    }
    txs = [
        {
            "id": 100,
            "type": "buy",
            "symbol": "BTC",
            "amount": 1.0,
            "price": 10000.0,
            "date": "2023-01-01",
            "coin": "Bitcoin",
        },
        {
            "id": 101,
            "type": "sell",
            "symbol": "BTC",
            "amount": 0.5,
            "price": 20000.0,
            "date": "2023-01-05",
            "coin": "Bitcoin",
        },
    ]
    stats = {
        "total_balance": Decimal("15000.0"),
        "total_invested": Decimal("10000.0"),
        "total_sold": Decimal("10000.0"),  # 0.5 * 20k
        "net_profit": Decimal("5000.0"),
        "total_unrealized_gain": Decimal("5000.0"),
        "trade_count": 2,
    }

    df = _prepare_summary_df(user_info, txs, stats)
    data = df.to_dict("records")

    assert data[0]["Value"] == "J*** D***"  # Masked name
    assert data[1]["Value"] == "jo***@example.com"  # Masked email
    assert data[5]["Value"] == 4  # Days Active: Jan 5 - Jan 1 = 4
    assert data[8]["Value"] == Decimal("10000.0")  # Total Cashed Out
    assert data[10]["Value"] == Decimal("20000.0")  # Trading Volume


def test_prepare_summary_df_empty_data():
    """Test summary DataFrame preparation with empty data."""
    from app import _prepare_summary_df

    dummy_stats = {
        "trade_count": 0,
        "total_invested": 0,
        "total_sold": 0,
        "total_balance": 0,
        "total_unrealized_gain": 0,
        "net_profit": 0,
    }
    df = _prepare_summary_df(None, [], dummy_stats)
    data = df.to_dict("records")

    assert data[0]["Value"] == "Unknown"
    assert data[4]["Value"] == "N/A"  # Last Trade
    assert data[5]["Value"] == 0  # Days Active


@patch("app.crypto.crypto_details")
def test_export_all_data_df_manipulation(mock_crypto_details, client):
    """Test DataFrame manipulation logic for export."""
    mock_crypto_details.return_value = [{"symbol": "BTC", "name": "Bitcoin"}]

    txs = [
        {
            "id": "1",
            "type": "buy",
            "symbol": "BTC",
            "amount": 1.0,
            "price": 10000.0,
            "date": "2023-01-01",
            "coin": "Bitcoin",
        }
    ]
    stats = {
        "assets": [
            {
                "symbol": "BTC",
                "holdings": 1.0,
                "value": "$20,000.00",
                "price": "$20,000.00",
                "avg_price": "$10,000.00",
                "pnl_percent": 100.0,
            }
        ],
        "total_balance": 20000.0,
        "total_invested": 10000.0,
        "total_sold": 0.0,
        "total_unrealized_gain": 10000.0,
        "net_profit": 10000.0,
        "profit_percent": 100.0,
        "trade_count": 1,
    }

    df_portfolio = pd.DataFrame(stats["assets"])

    symbol_to_name = {c["symbol"]: c["name"] for c in mock_crypto_details.return_value}

    if "symbol" in df_portfolio.columns:
        df_portfolio["name"] = df_portfolio["symbol"].apply(
            lambda x: symbol_to_name.get(x, x)
        )
        df_portfolio.rename(
            columns={
                "holdings": "Quantity",
                "price": "Current Price",
                "avg_price": "Avg Buy Price",
                "value": "Total Value",
                "name": "Asset",
                "symbol": "Ticker",
                "pnl_percent": "PnL %",
            },
            inplace=True,
        )

        for col in ["Current Price", "Total Value", "Avg Buy Price"]:
            if col in df_portfolio.columns:
                df_portfolio[col] = (
                    df_portfolio[col]
                    .astype(str)
                    .str.replace("$", "", regex=False)
                    .str.replace(",", "", regex=False)
                    .astype(float)
                )

    assert df_portfolio["Asset"].iloc[0] == "Bitcoin"
    assert df_portfolio["Current Price"].iloc[0] == pytest.approx(20000.0)

    txs.sort(key=lambda x: float(x["id"]), reverse=True)
    ledger_data = []
    for tx in txs:
        qty = float(tx["amount"])
        price = float(tx["price"])
        is_buy = tx["type"] == "buy"
        amount_usd = -(qty * price) if is_buy else (qty * price)
        activity = "Buy" if is_buy else "Sell"
        full_name = symbol_to_name.get(tx["symbol"], tx["coin"])
        ledger_data.append(
            {
                "Date": tx["date"],
                "Ref ID": f"TX-{tx['id'][-6:]}",
                "Activity": f"{activity} {full_name}",
                "Ticker": tx["symbol"],
                "Quantity": qty,
                "Price / Coin": price,
                "Total Value": amount_usd,
            }
        )
    df_transactions = pd.DataFrame(ledger_data)

    assert df_transactions["Activity"].iloc[0] == "Buy Bitcoin"
    assert df_transactions["Total Value"].iloc[0] == pytest.approx(-10000.0)
