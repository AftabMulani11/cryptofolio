"""
Unit tests for database operations.
"""

# pylint: disable=redefined-outer-name, wrong-import-position
import sys
import os
from collections import defaultdict
from decimal import Decimal
import pytest
from moto import mock_aws
from botocore.exceptions import ClientError, BotoCoreError
from argon2.exceptions import VerifyMismatchError

# FIX: Add parent directory to path so imports resolve correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the module and its dependencies using absolute imports
from database.operations import (
    login_user,
    split_name,
    to_decimal,
    add_user,
    is_email_available,
    get_user_details,
    reset_password,
    update_password,
    add_transaction_db,
    get_transactions_db,
    update_transaction_db,
    delete_transaction_db,
    update_user_details,
    get_user_holdings,
    validate_ledger_impact,
    calculate_portfolio_stats,
    _aggregate_holdings,
    _process_transaction,
    _create_asset_record,
)
from database import operations
from database import db
from database.table import user_details_table


# Constants for testing
MOCK_PASSWORD = "SafeTestPassword123!"
MOCK_NEW_PASSWORD = "NewSafePassword456!"
MOCK_WRONG_PASSWORD = "WrongPassword!"


@pytest.fixture(scope="session", autouse=True)
def setup_mock_dynamodb():
    """
    Setup fixture to create all necessary tables within the moto mocked environment.
    This fixture ensures the tables exist for ALL tests.
    """
    # Start moto mocking for the entire session
    mock = mock_aws()
    mock.start()

    # Re-initialize the global resource to point to the mock client
    mock_dynamo = db.db_resource()
    operations._dynamo = mock_dynamo
    # Update external reference if used
    operations.dynamodb = mock_dynamo

    # Create all tables explicitly in the mocked environment
    user_details_table("user_details")
    user_details_table("login_details")
    user_details_table("user_portfolio")

    # Update internal module references to use the mocked resources
    # This is CRITICAL: operations.py uses _user_tbl, not user_table
    operations._user_tbl = mock_dynamo.Table("user_details")
    operations._login_tbl = mock_dynamo.Table("login_details")
    operations._portfolio_tbl = mock_dynamo.Table("user_portfolio")

    # Update external aliases used in tests so patches work on the same objects
    operations.user_table = operations._user_tbl
    operations.login_table = operations._login_tbl
    operations.portfolio_table = operations._portfolio_tbl

    # Ensure tables are empty before yield
    operations.login_table.scan = lambda **k: {"Items": []}
    operations.user_table.scan = lambda **k: {"Items": []}
    operations.portfolio_table.scan = lambda **k: {"Items": []}

    yield

    mock.stop()


# --- Utility Function Tests ---


def test_split_name_full():
    """Test splitting a full name (First Last)."""
    first, last = split_name("Elon Musk")
    assert first == "Elon"
    assert last == "Musk"


def test_split_name_single():
    """Test splitting a single name."""
    first, last = split_name("Cher")
    assert first == "Cher"
    assert last == ""


def test_split_name_empty():
    """Test splitting an empty name."""
    first, last = split_name("")
    assert first == ""
    assert last == ""


def test_to_decimal_standard():
    """Test converting a standard float to Decimal."""
    assert to_decimal(123.45) == Decimal("123.45")


def test_to_decimal_string_number():
    """Test converting a string number to Decimal."""
    assert to_decimal("99.99") == Decimal("99.99")


def test_to_decimal_invalid_input():
    """Test converting invalid input returns Decimal('0.0')."""
    assert to_decimal(None) == Decimal("0.0")
    assert to_decimal("not_a_number") == Decimal("0.0")


# --- Authentication Tests ---


def test_login_user_success(mocker):
    """Test successful user login."""
    # PATCH: changed from ph to _password_hasher
    mock_ph = mocker.patch("database.operations._password_hasher")
    mock_ph.verify.return_value = True

    mocker.patch.object(
        operations.login_table,
        "get_item",
        return_value={
            "Item": {
                "username": "testuser",
                "password": "mock_hashed_password",
                "user_id": "123",
            }
        },
    )

    result = login_user("testuser", MOCK_PASSWORD)
    assert result["status"] == "success"
    assert result["message"] == "Login successful"


def test_login_user_incorrect_password(mocker):
    """Test login with incorrect password."""
    # PATCH: changed from ph to _password_hasher
    mock_ph = mocker.patch("database.operations._password_hasher")
    mock_ph.verify.side_effect = VerifyMismatchError

    mocker.patch.object(
        operations.login_table,
        "get_item",
        return_value={
            "Item": {
                "username": "testuser",
                "password": "mock_hashed_password",
                "user_id": "123",
            }
        },
    )

    result = login_user("testuser", MOCK_WRONG_PASSWORD)
    assert result["status"] == "error"
    assert result["message"] == "Incorrect password"


def test_login_user_not_found(mocker):
    """Test login attempt for a non-existent user."""
    mocker.patch.object(operations.login_table, "get_item", return_value={})
    result = login_user("nonexistent", MOCK_PASSWORD)
    assert result["status"] == "error"
    assert result["message"] == "User not found"


def test_login_user_db_error(mocker):
    """Test login attempt when there is an error accessing the login table."""
    mocker.patch.object(
        operations.login_table,
        "get_item",
        side_effect=ClientError(
            {"Error": {"Code": "ProvisionedThroughputExceededException"}}, "GetItem"
        ),
    )
    result = login_user("anyuser", "anypassword")
    assert result["status"] == "error"
    assert "DB Error: An error occurred" in result["message"]


# --- User Management Tests ---


def test_add_user_success(mocker):
    """Test adding a new user successfully."""
    # PATCH: changed paths
    mocker.patch("database.operations.is_email_available", return_value=True)
    mocker.patch.object(operations.login_table, "put_item", return_value={})
    mocker.patch.object(operations.user_table, "put_item", return_value={})

    # PATCH: changed from ph to _password_hasher
    mock_ph = mocker.patch("database.operations._password_hasher")
    mock_ph.hash.return_value = "hashed_pw"

    mocker.patch("time.time", return_value=1609459200)

    result = add_user("new@example.com", "newuser", "New User", MOCK_PASSWORD)
    assert result["status"] == "success"
    operations.login_table.put_item.assert_called_once()
    operations.user_table.put_item.assert_called_once()


def test_add_user_email_exists(mocker):
    """Test adding a user when email is already in use."""
    mocker.patch("database.operations.is_email_available", return_value=False)
    result = add_user("existing@example.com", "newuser", "New User", MOCK_PASSWORD)
    assert result["status"] == "error"
    assert "Email already exists" in result["message"]


def test_add_user_username_taken(mocker):
    """Test adding a user when username is already taken."""
    mocker.patch("database.operations.is_email_available", return_value=True)
    # PATCH: changed from ph to _password_hasher
    mocker.patch("database.operations._password_hasher")
    mocker.patch.object(
        operations.login_table,
        "put_item",
        side_effect=ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem"
        ),
    )

    result = add_user("new@example.com", "existinguser", "New User", MOCK_PASSWORD)
    assert result["status"] == "error"
    assert "Username already taken" in result["message"]


def test_is_email_available_unavailable(mocker):
    """Test email unavailable case."""
    mocker.patch.object(
        operations.user_table,
        "query",
        return_value={"Count": 1, "Items": [{"email": "test@test.com"}]},
    )
    assert is_email_available("test@test.com") is False


def test_is_email_available_db_error(mocker):
    """Test DB error during email check."""
    mocker.patch.object(operations.user_table, "query", side_effect=BotoCoreError())
    assert is_email_available("test@test.com") is False


def test_get_user_details_success(mocker):
    """Test fetching user details successfully."""
    mock_item = {
        "email": "test@test.com",
        "username": "testuser",
        "user_id": "123",
        "first_name": "Test",
        "last_name": "User",
        "join_date": "Jan 2023",
    }
    mocker.patch.object(
        operations.user_table, "query", return_value={"Count": 1, "Items": [mock_item]}
    )
    result = get_user_details("testuser")
    assert result["name"] == "Test User"
    assert result["email"] == "test@test.com"


def test_get_user_details_not_found(mocker):
    """Test fetching details for non-existent user."""
    mocker.patch.object(
        operations.user_table, "query", return_value={"Count": 0, "Items": []}
    )
    assert get_user_details("nonexistent") is None


def test_get_user_details_db_error(mocker):
    """Test DB error during details fetch."""
    mocker.patch.object(operations.user_table, "query", side_effect=BotoCoreError())
    assert get_user_details("testuser") is None


def test_reset_password_success(mocker):
    """Test successful password reset."""
    mocker.patch.object(
        operations.user_table,
        "query",
        return_value={"Items": [{"email": "test@test.com"}]},
    )
    mocker.patch.object(operations.login_table, "update_item", return_value={})

    # PATCH: changed from ph to _password_hasher
    mock_ph = mocker.patch("database.operations._password_hasher")
    mock_ph.hash.return_value = "new_hashed_pw"

    result = reset_password("testuser", "test@test.com", MOCK_NEW_PASSWORD)
    assert result["status"] == "success"


def test_reset_password_invalid_credentials(mocker):
    """Test password reset failure with invalid username/email."""
    mocker.patch.object(
        operations.user_table,
        "query",
        return_value={"Items": [{"email": "wrong@test.com"}]},
    )
    result = reset_password("testuser", "test@test.com", MOCK_NEW_PASSWORD)
    assert result["status"] == "error"
    assert "Invalid username/email" in result["message"]


def test_update_password_success(mocker):
    """Test successful password update."""
    mocker.patch("database.operations.login_user", return_value={"status": "success"})
    mocker.patch.object(operations.login_table, "update_item", return_value={})

    # PATCH: changed from ph to _password_hasher
    mock_ph = mocker.patch("database.operations._password_hasher")
    mock_ph.hash.return_value = "new_hashed_pw"

    result = update_password("testuser", MOCK_PASSWORD, MOCK_NEW_PASSWORD)
    assert result["status"] == "success"


def test_update_password_same_password(mocker):
    """Test password update failure when new password is the same as current."""
    mocker.patch("database.operations.login_user", return_value={"status": "success"})
    result = update_password("testuser", MOCK_PASSWORD, MOCK_PASSWORD)
    assert result["status"] == "error"
    assert "New password cannot be same as current" in result["message"]


def test_update_password_auth_failure(mocker):
    """Test password update failure due to incorrect current password."""
    mock_login_failure = {"status": "error", "message": "Incorrect password"}
    mocker.patch("database.operations.login_user", return_value=mock_login_failure)
    result = update_password("testuser", MOCK_WRONG_PASSWORD, MOCK_NEW_PASSWORD)
    assert result == mock_login_failure


def test_update_user_details_name_update_success(mocker):
    """Test updating only the name successfully."""
    mocker.patch(
        "database.operations.get_user_details",
        return_value={"name": "Old Name", "email": "a@b.com", "join_date": "Jan 2023"},
    )
    mocker.patch.object(operations.user_table, "update_item", return_value={})
    result = update_user_details("testuser", {"name": "New Name", "email": "a@b.com"})
    assert result["status"] == "success"
    operations.user_table.update_item.assert_called_once()


# --- Transaction & Holdings Tests ---


@pytest.fixture
def transactions_fixture():
    """Mock transaction data."""
    return [
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
            "type": "buy",
            "symbol": "ETH",
            "amount": 5.0,
            "price": 1000.0,
            "date": "2023-01-02",
            "coin": "Ethereum",
        },
        {
            "id": 102,
            "type": "sell",
            "symbol": "BTC",
            "amount": 0.5,
            "price": 15000.0,
            "date": "2023-01-03",
            "coin": "Bitcoin",
        },
    ]


def test_process_transaction_buy():
    """Test processing a buy transaction."""
    holdings = defaultdict(lambda: Decimal("0.0"))
    cost_basis = defaultdict(lambda: Decimal("0.0"))
    tx = {"type": "buy", "symbol": "BTC", "amount": 1.0, "price": 10000.0}

    invested, sold = _process_transaction(tx, holdings, cost_basis)

    assert holdings["BTC"] == Decimal("1.0")
    assert cost_basis["BTC"] == Decimal("10000.0")
    assert invested == Decimal("10000.0")
    assert sold == Decimal("0.0")


def test_process_transaction_sell_positive_holdings():
    """Test processing a sell transaction with existing holdings."""
    holdings = defaultdict(lambda: Decimal("0.0"))
    cost_basis = defaultdict(lambda: Decimal("0.0"))
    holdings["BTC"] = Decimal("2.0")
    cost_basis["BTC"] = Decimal("20000.0")

    tx = {"type": "sell", "symbol": "BTC", "amount": 1.0, "price": 15000.0}

    invested, sold = _process_transaction(tx, holdings, cost_basis)

    assert holdings["BTC"] == Decimal("1.0")
    assert cost_basis["BTC"] == Decimal("10000.0")
    assert invested == Decimal("0.0")
    assert sold == Decimal("15000.0")


def test_aggregate_holdings(transactions_fixture):
    """Test aggregation of holdings and costs."""
    holdings, invested, sold, buy_stats = _aggregate_holdings(transactions_fixture)

    assert holdings["BTC"] == Decimal("0.5")
    assert holdings["ETH"] == Decimal("5.0")
    assert invested == Decimal("15000.0")
    assert sold == Decimal("7500.0")
    assert buy_stats["BTC"]["qty"] == Decimal("0.5")
    assert buy_stats["BTC"]["cost"] == Decimal("5000.0")


def test_get_user_holdings_integration(mocker, transactions_fixture):
    """Test get_user_holdings function."""
    mocker.patch(
        "database.operations.get_transactions_db", return_value=transactions_fixture
    )
    assert get_user_holdings("testuser", "BTC") == pytest.approx(0.5)
    assert get_user_holdings("testuser", "ETH") == pytest.approx(5.0)
    assert get_user_holdings("testuser", "XRP") == pytest.approx(0.0)


def test_validate_ledger_impact_success(mocker):
    """Test validation success (enough funds for sell)."""
    mocker.patch("database.operations.get_user_holdings", return_value=1.0)
    assert validate_ledger_impact("testuser", "BTC", -0.5) is True


def test_validate_ledger_impact_failure(mocker):
    """Test validation failure (not enough funds for sell)."""
    mocker.patch("database.operations.get_user_holdings", return_value=1.0)
    with pytest.raises(ValueError) as excinfo:
        validate_ledger_impact("testuser", "BTC", -1.5)
    assert "Insufficient funds." in str(excinfo.value)


def test_add_transaction_db_success_buy(mocker):
    """Test adding a buy transaction."""
    mocker.patch.object(operations.portfolio_table, "put_item", return_value={})
    mocker.patch("time.time", return_value=1234567.89)
    tx_data = {
        "type": "buy",
        "coin": "Bitcoin",
        "symbol": "BTC",
        "amount": 0.1,
        "price": 10000,
        "date": "2024-01-01",
    }

    result = add_transaction_db("testuser", tx_data)
    assert result["type"] == "buy"
    assert result["id"] == "1234567890"


def test_add_transaction_db_sell_validation_failure(mocker):
    """Test adding a sell transaction that fails validation."""
    mocker.patch(
        "database.operations.validate_ledger_impact",
        side_effect=ValueError("Insufficient funds."),
    )
    tx_data = {
        "type": "sell",
        "symbol": "BTC",
        "amount": 100,
        "price": 10,
        "date": "2024-01-01",
    }

    result = add_transaction_db("testuser", tx_data)
    assert "error" in result
    assert "Insufficient funds." in result["error"]


def test_get_transactions_db_success(mocker):
    """Test fetching all transactions."""
    mock_items = [
        {
            "username": "testuser",
            "tx_id": "1",
            "type": "buy",
            "coin": "A",
            "symbol": "A",
            "amount": "1.0",
            "price": "100.0",
            "date": "2024-01-01",
        }
    ]
    mocker.patch.object(
        operations.portfolio_table, "query", return_value={"Items": mock_items}
    )

    txs = get_transactions_db("testuser")
    assert len(txs) == 1
    assert txs[0]["amount"] == pytest.approx(1.0)


def test_get_transactions_db_db_error(mocker):
    """Test fetching transactions returns empty list on DB error."""
    mocker.patch.object(
        operations.portfolio_table, "query", side_effect=BotoCoreError()
    )
    assert get_transactions_db("testuser") == []


def test_update_transaction_db_success(mocker):
    """Test updating a transaction successfully."""
    mocker.patch("database.operations.get_user_holdings", return_value=1.0)
    old_tx = {
        "username": "testuser",
        "tx_id": "1",
        "type": "buy",
        "coin": "A",
        "symbol": "BTC",
        "amount": "1.0",
        "price": "10000",
        "date": "2024-01-01",
    }
    mocker.patch.object(
        operations.portfolio_table, "get_item", return_value={"Item": old_tx}
    )
    mocker.patch("database.operations.validate_ledger_impact", return_value=True)
    mocker.patch.object(operations.portfolio_table, "update_item", return_value={})

    new_tx_data = {
        "id": "1",
        "type": "sell",
        "amount": 0.5,
        "price": 20000,
        "date": "2024-01-02",
    }
    result = update_transaction_db("testuser", new_tx_data)
    assert result["status"] == "success"


def test_update_transaction_db_not_found(mocker):
    """Test update transaction when ID is missing or not found."""
    mocker.patch.object(operations.portfolio_table, "get_item", return_value={})
    result = update_transaction_db("testuser", {"id": "999"})
    assert "error" in result


def test_update_transaction_db_validation_failure(mocker):
    """Test update transaction when it fails ledger validation."""
    old_tx = {
        "username": "testuser",
        "tx_id": "1",
        "type": "buy",
        "coin": "A",
        "symbol": "BTC",
        "amount": "1.0",
        "price": "10000",
        "date": "2024-01-01",
    }
    mocker.patch.object(
        operations.portfolio_table, "get_item", return_value={"Item": old_tx}
    )
    mocker.patch(
        "database.operations.validate_ledger_impact",
        side_effect=ValueError("Validation failed."),
    )

    new_tx_data = {
        "id": "1",
        "type": "sell",
        "amount": 100,
        "price": 20000,
        "date": "2024-01-02",
    }
    result = update_transaction_db("testuser", new_tx_data)
    assert "Validation failed." in result["error"]


def test_delete_transaction_db_success(mocker):
    """Test deleting a transaction successfully."""
    mocker.patch("database.operations.get_user_holdings", return_value=1.0)
    old_tx = {
        "username": "testuser",
        "tx_id": "1",
        "type": "buy",
        "coin": "A",
        "symbol": "BTC",
        "amount": "0.5",
        "price": "10000",
        "date": "2024-01-01",
    }
    mocker.patch.object(
        operations.portfolio_table, "get_item", return_value={"Item": old_tx}
    )
    mocker.patch("database.operations.validate_ledger_impact", return_value=True)
    mocker.patch.object(operations.portfolio_table, "delete_item", return_value={})

    result = delete_transaction_db("testuser", "1")
    assert result["status"] == "success"


def test_delete_transaction_db_sell_impact_success(mocker):
    """Test deleting a sell transaction (positive impact) successfully."""
    mocker.patch("database.operations.get_user_holdings", return_value=0.5)
    old_tx = {
        "username": "testuser",
        "tx_id": "1",
        "type": "sell",
        "coin": "A",
        "symbol": "BTC",
        "amount": "0.5",
        "price": "10000",
        "date": "2024-01-01",
    }
    mocker.patch.object(
        operations.portfolio_table, "get_item", return_value={"Item": old_tx}
    )
    mocker.patch("database.operations.validate_ledger_impact", return_value=True)
    mocker.patch.object(operations.portfolio_table, "delete_item", return_value={})

    result = delete_transaction_db("testuser", "1")
    assert result["status"] == "success"


def test_delete_transaction_db_not_found(mocker):
    """Test delete transaction when not found."""
    mocker.patch.object(operations.portfolio_table, "get_item", return_value={})
    result = delete_transaction_db("testuser", "999")
    assert "error" in result


def test_delete_transaction_db_validation_failure(mocker):
    """Test delete transaction when it fails ledger validation."""
    old_tx = {
        "username": "testuser",
        "tx_id": "1",
        "type": "buy",
        "coin": "A",
        "symbol": "BTC",
        "amount": "10.0",
        "price": "10000",
        "date": "2024-01-01",
    }
    mocker.patch.object(
        operations.portfolio_table, "get_item", return_value={"Item": old_tx}
    )
    mocker.patch(
        "database.operations.validate_ledger_impact",
        side_effect=ValueError("Validation failed."),
    )

    result = delete_transaction_db("testuser", "1")
    assert "Validation failed." in result["error"]


# --- Portfolio Calculation Tests ---


@pytest.fixture
def live_ws_data():
    """Mock websocket data."""
    return {
        "btcusdt": {
            "symbol": "BTCUSDT",
            "close": 20000.0,
            "change": 10.0,
            "high": 21000,
            "low": 19000,
            "volume": 10000,
        },
        "ethusdt": {
            "symbol": "ETHUSDT",
            "close": 2000.0,
            "change": 5.0,
            "high": 2100,
            "low": 1900,
            "volume": 5000,
        },
    }


def test_create_asset_record_success(live_ws_data):
    """Test asset record creation, including PnL calculation."""
    sym = "BTC"
    qty = Decimal("0.5")
    buy_stats = {"BTC": {"qty": Decimal("1.0"), "cost": Decimal("10000.0")}}

    record = _create_asset_record(sym, qty, buy_stats, live_ws_data)

    assert record["symbol"] == "BTC"
    assert record["raw_price"] == pytest.approx(20000.0)
    assert record["holdings"] == "0.5000"
    assert record["value"] == "$10,000.00"
    assert record["avg_price"] == "$10,000.00"
    assert record["pnl_percent"] == pytest.approx(100.0)


def test_create_asset_record_no_price(live_ws_data):
    """Test asset record creation when no live price is available."""
    sym = "UNK"
    qty = Decimal("1")
    buy_stats = {"UNK": {"qty": Decimal("10"), "cost": Decimal("100")}}

    record = _create_asset_record(sym, qty, buy_stats, live_ws_data)

    assert record["raw_price"] == pytest.approx(0.0)
    assert record["value"] == "$0.00"
    assert record["pnl_percent"] == pytest.approx(-100.0)


def test_calculate_portfolio_stats_full_flow(transactions_fixture, live_ws_data):
    """Test the full portfolio stats calculation."""
    stats = calculate_portfolio_stats(transactions_fixture, live_ws_data)

    assert stats["total_balance"] == pytest.approx(20000.0)
    assert stats["total_invested"] == pytest.approx(15000.0)
    assert stats["total_sold"] == pytest.approx(7500.0)
    assert stats["total_unrealized_gain"] == pytest.approx(10000.0)
    assert stats["net_profit"] == pytest.approx(12500.0)
    assert stats["profit_percent"] == pytest.approx(83.33, abs=0.1)
    assert stats["trade_count"] == 3
    assert stats["best_performer"]["symbol"] == "BTC"
    assert stats["assets"][0]["symbol"] == "BTC"
    assert stats["assets"][0]["allocation"] == pytest.approx(50.0)
    assert stats["assets"][1]["symbol"] == "ETH"
    assert stats["assets"][1]["allocation"] == pytest.approx(50.0)


def test_calculate_portfolio_stats_empty_transactions(live_ws_data):
    """Test stats calculation with no transactions."""
    stats = calculate_portfolio_stats([], live_ws_data)

    assert stats["total_balance"] == pytest.approx(0.0)
    assert stats["net_profit"] == pytest.approx(0.0)
    assert stats["profit_percent"] == pytest.approx(0.0)
    assert stats["trade_count"] == 0
    assert stats["best_performer"] == {"symbol": "-", "change": "0.00%"}
    assert stats["assets"] == []


# --- update_user_details Tests ---


def test_update_user_details_db_update_error(mocker):
    """Test update user details failure due to DB error (non-email change)."""
    mocker.patch(
        "database.operations.get_user_details",
        return_value={"name": "Old Name", "email": "a@b.com", "join_date": "Jan 2023"},
    )
    mocker.patch.object(
        operations.user_table, "update_item", side_effect=BotoCoreError()
    )

    result = update_user_details("testuser", {"name": "New Name", "email": "a@b.com"})
    assert "Update failed" in result["error"]


def test_update_user_details_email_update_success(mocker):
    """Test successful email and name update (transact_write_items success)."""
    mocker.patch(
        "database.operations.get_user_details",
        return_value={
            "name": "Old Name",
            "email": "old@b.com",
            "join_date": "Jan 2023",
        },
    )
    old_item_resp = {
        "Items": [{"email": "old@b.com", "username": "testuser", "user_id": "123"}]
    }
    mocker.patch.object(operations.user_table, "query", return_value=old_item_resp)
    mocker.patch.object(
        operations.dynamodb.meta.client, "transact_write_items", return_value={}
    )

    new_data = {"name": "New Name", "email": "new@c.com"}
    result = update_user_details("testuser", new_data)

    assert result["status"] == "success"
    operations.dynamodb.meta.client.transact_write_items.assert_called_once()


def test_update_user_details_email_update_email_taken(mocker):
    """Test email update failure due to ConditionalCheckFailedException."""
    mocker.patch(
        "database.operations.get_user_details",
        return_value={
            "name": "Old Name",
            "email": "old@b.com",
            "join_date": "Jan 2023",
        },
    )
    old_item_resp = {
        "Items": [{"email": "old@b.com", "username": "testuser", "user_id": "123"}]
    }
    mocker.patch.object(operations.user_table, "query", return_value=old_item_resp)
    mocker.patch.object(
        operations.dynamodb.meta.client,
        "transact_write_items",
        side_effect=ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}}, "TransactWriteItems"
        ),
    )

    new_data = {"name": "New Name", "email": "new@c.com"}
    result = update_user_details("testuser", new_data)

    assert "Update failed" in result["error"]


def test_update_user_details_not_found(mocker):
    """Test update user details when user is not found."""
    mocker.patch("database.operations.get_user_details", return_value=None)
    result = update_user_details("nonexistent", {"name": "New Name"})
    assert "User not found" in result["error"]
