"""
Database Operations Module.

Handles all business logic related to user data, portfolios, and authentication.
"""

import time
import uuid
from datetime import datetime
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from botocore.exceptions import ClientError, BotoCoreError, NoCredentialsError
from boto3.dynamodb.conditions import Key
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Local package imports (relative)
from . import table as table_module
from . import db as db_module

# tiny wrapper for prints so we can swap to logging easily later
LOG_PREFIX = "db>"


def _log(*parts):
    # human: prefer small prints while developing; replace later with logging.getLogger(...)
    print(LOG_PREFIX, *parts)


# password hasher instance
_password_hasher = PasswordHasher()

# Dynamo resource and table handles
_dynamo = db_module.db_resource()
_user_tbl = table_module.user_details_table("user_details")
_login_tbl = table_module.user_details_table("login_details")
_portfolio_tbl = table_module.user_details_table("user_portfolio")


# --- HELPER FUNCTIONS ---


def safe_str(val, default=""):
    """Safely converts a possibly-None value to string."""
    # small extra check: explicitly treat bytes separately (some callers pass bytes)
    if val is None:
        return default
    if isinstance(val, bytes):
        try:
            return val.decode("utf-8")
        except Exception:  # pylint: disable=broad-exception-caught
            return str(val)
    return str(val)


def split_name(full_name):
    """Split a full name into (first, last). Keeps last as remaining parts."""
    if not full_name:
        return "", ""
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0], ""
    # intentionally keep the remainder joined (human tendency)
    return parts[0], " ".join(parts[1:])


def to_decimal(value):
    """Safely convert a value to Decimal; returns Decimal('0.0') on failure."""
    try:
        # Give Decimal a string input to avoid float precision surprises
        return Decimal(str(value))
    except (ValueError, TypeError, AttributeError, InvalidOperation):
        # human note: used to log these but removed for noise
        return Decimal("0.0")


def _process_transaction(tx, holdings, cost_basis):
    """
    Update holdings and cost basis for a single transaction.
    Returns (invested_amount, sold_amount) as Decimal values.
    """
    # intentionally verbose variable names to make debugging with pdb easier
    amount = to_decimal(tx["amount"])
    price = to_decimal(tx["price"])
    value_usd = amount * price
    symbol = tx["symbol"]

    invested = Decimal("0.0")
    sold = Decimal("0.0")

    if tx["type"] == "buy":
        # human note: accidentally left a redundant conversion once, kept it as habit
        holdings[symbol] = holdings[symbol] + amount
        cost_basis[symbol] = cost_basis[symbol] + value_usd
        invested = value_usd

    elif tx["type"] == "sell":
        current_avg_price = Decimal("0.0")
        if holdings[symbol] > Decimal("0.0"):
            # defensive: avoid division by zero
            try:
                current_avg_price = cost_basis[symbol] / holdings[symbol]
            except (InvalidOperation, ZeroDivisionError):
                current_avg_price = Decimal("0.0")

        cost_of_sold_coins = amount * current_avg_price
        cost_basis[symbol] = cost_basis[symbol] - cost_of_sold_coins
        holdings[symbol] = holdings[symbol] - amount

        # human-ish clamping to avoid negatives creeping in
        if holdings[symbol] < Decimal("0.0"):
            holdings[symbol] = Decimal("0.0")
        if cost_basis[symbol] < Decimal("0.0"):
            cost_basis[symbol] = Decimal("0.0")

        sold = value_usd

    # return values intentionally left as Decimal
    return invested, sold


def _aggregate_holdings(transactions):
    """
    Aggregate transactions into holdings and cost basis totals.
    Uses Decimal for numeric precision.
    """
    # keep original sort order stable and deterministic
    sorted_txs = sorted(transactions, key=lambda x: x["id"])
    holdings = defaultdict(lambda: Decimal("0.0"))
    cost_basis = defaultdict(lambda: Decimal("0.0"))

    total_invested_lifetime = Decimal("0.0")
    total_sold_lifetime = Decimal("0.0")

    for tx in sorted_txs:
        inv, sld = _process_transaction(tx, holdings, cost_basis)
        total_invested_lifetime += inv
        total_sold_lifetime += sld

    # build a buy_stats map used elsewhere
    buy_stats = {}
    for sym, qty in holdings.items():
        buy_stats[sym] = {"qty": qty, "cost": cost_basis[sym]}

    return holdings, total_invested_lifetime, total_sold_lifetime, buy_stats


def _create_asset_record(sym, qty, buy_stats, ws_data):
    """
    Build a single asset record for frontend consumption.
    Returns a dict with both display strings and raw numeric fields used internally.
    """
    ws_key = f"{sym.lower()}usdt"
    ws_item = ws_data.get(ws_key, {}) if isinstance(ws_data, dict) else {}

    current_price = to_decimal(ws_item.get("close", 0.0))
    value = qty * current_price

    avg_price = Decimal("0.0")
    stats = buy_stats.get(sym)

    if stats and stats.get("qty", Decimal("0.0")) > Decimal("0.0"):
        # be defensive on division
        try:
            avg_price = stats["cost"] / stats["qty"]
        except (InvalidOperation, ZeroDivisionError):
            avg_price = Decimal("0.0")

    cost_basis_val = qty * avg_price
    asset_pnl_percent = Decimal("0.0")

    if cost_basis_val > Decimal("0.0"):
        asset_pnl_percent = ((value - cost_basis_val) / cost_basis_val) * Decimal("100")

    # human-friendly formatted strings kept for backward compatibility with front-end
    return {
        "symbol": sym,
        "name": sym,  # placeholder; front-end can map to full name if needed
        "price": f"${current_price:,.2f}",
        "raw_price": float(current_price),
        "holdings": f"{qty:.4f}",
        "value": f"${value:,.2f}",
        "avg_price": f"${avg_price:,.2f}",
        "allocation": 0,  # populated later
        "change_24h": ws_item.get("change", 0.0),
        "pnl_percent": float(asset_pnl_percent),
        # helper raw decimals for aggregation only (removed before returning to client in other layer)
        "raw_value_dec": value,
        "raw_cost_basis": cost_basis_val,
    }


def _calculate_valuations(holdings, buy_stats, ws_data):
    """
    For each holding, compute current market valuation and PnL.
    Returns (assets_list, total_balance, total_cost_basis)
    """
    assets_list = []
    total_balance = Decimal("0.0")
    current_cost_basis_total = Decimal("0.0")

    for sym, qty in holdings.items():
        # tiny threshold to ignore dust positions
        if qty <= Decimal("0.00000001"):
            continue

        rec = _create_asset_record(sym, qty, buy_stats, ws_data)

        # accumulate using raw decimal helpers
        total_balance += rec["raw_value_dec"]
        current_cost_basis_total += rec["raw_cost_basis"]

        # remove internals before appending to returned list (but keep some for debugging if needed)
        del rec["raw_value_dec"]
        del rec["raw_cost_basis"]

        assets_list.append(rec)

    return assets_list, total_balance, current_cost_basis_total


def calculate_portfolio_stats(transactions, ws_data):
    """
    Public function to compute portfolio statistics.
    Returns a dictionary with numbers (floats) suitable for JSON serialization.
    """
    holdings, total_invested, total_sold, buy_stats = _aggregate_holdings(transactions)
    assets_list, total_balance_now, current_cost_basis = _calculate_valuations(
        holdings, buy_stats, ws_data
    )

    # compute allocation per asset (a bit verbose; human devs love intermediate vars)
    for asset in assets_list:
        try:
            if total_balance_now > Decimal("0.0"):
                # convert asset price & holdings back into decimals for allocation calc
                val_dec = to_decimal(asset["raw_price"]) * to_decimal(asset["holdings"])
                allocation = (val_dec / total_balance_now) * Decimal("100")
                asset["allocation"] = float(allocation)
        except Exception:  # pylint: disable=broad-exception-caught
            # if anything odd happens, leave allocation as 0
            asset["allocation"] = 0

    net_profit = (total_balance_now + total_sold) - total_invested

    profit_percent = Decimal("0.0")
    if total_invested > Decimal("0.0"):
        try:
            profit_percent = (net_profit / total_invested) * Decimal("100")
        except Exception:  # pylint: disable=broad-exception-caught
            profit_percent = Decimal("0.0")

    total_unrealized_gain = total_balance_now - current_cost_basis

    # pick best performer by pnl_percent (assets_list might be empty)
    best_performer = {"symbol": "-", "change": "0.00%"}
    if assets_list:
        best_asset = max(assets_list, key=lambda x: x.get("pnl_percent", 0.0))
        best_performer = {
            "symbol": best_asset.get("symbol", "-"),
            "change": f"{best_asset.get('pnl_percent', 0.0):+.2f}%",
        }

    # Return floats for JSON serialization (frontend expects floats)
    return {
        "assets": assets_list,
        "total_balance": float(total_balance_now),
        "total_invested": float(total_invested),
        "total_sold": float(total_sold),
        "total_unrealized_gain": float(total_unrealized_gain),
        "net_profit": float(net_profit),
        "profit_percent": float(profit_percent),
        "best_performer": best_performer,
        "trade_count": len(transactions),
    }


def get_user_holdings(username, symbol):
    """Return aggregated holdings for a user and symbol as a float."""
    txs = get_transactions_db(username)
    total = Decimal("0.0")
    for tx in txs:
        if tx.get("symbol") == symbol:
            amt = to_decimal(tx.get("amount"))
            if tx.get("type") == "buy":
                total += amt
            elif tx.get("type") == "sell":
                total -= amt
    # explicit cast to float for callers
    return float(total)


def validate_ledger_impact(username, symbol, change_in_balance):
    """
    Validate that a proposed change won't make holdings go below an allowable negative threshold.
    Raises ValueError on insufficient funds.
    """
    change = to_decimal(change_in_balance)
    current_balance = to_decimal(get_user_holdings(username, symbol))
    projected_balance = current_balance + change

    # Allow a tiny negative tolerance due to rounding quirks
    if projected_balance < Decimal("-0.00000001"):
        raise ValueError(
            f"Insufficient funds. Result: {projected_balance:.4f} {symbol}."
        )
    return True


def login_user(username, password):
    """Authenticate user by verifying stored Argon2 hash."""
    try:
        response = _login_tbl.get_item(Key={"username": username})
        if "Item" not in response:
            return {"status": "error", "message": "User not found"}

        stored_password = response["Item"].get("password", "")
        # Argon2 verify raises VerifyMismatchError on mismatch
        _password_hasher.verify(stored_password, password)
        return {"status": "success", "message": "Login successful"}
    except VerifyMismatchError:
        return {"status": "error", "message": "Incorrect password"}
    except (ClientError, BotoCoreError, NoCredentialsError) as e:
        _log("login_user DB error:", e)
        return {"status": "error", "message": f"DB Error: {str(e)}"}
    except Exception as e:  # pylint: disable=broad-exception-caught
        _log("login_user unexpected error:", e)
        return {"status": "error", "message": "Authentication failed"}


def add_user(email, username, full_name, password):
    """Register a new user, storing both login and profile records."""
    # quick validation: email uniqueness
    if not is_email_available(email):
        return {"status": "error", "message": "Email already exists"}

    user_id = str(uuid.uuid4())
    first_name, last_name = split_name(full_name)
    current_date = datetime.now().strftime("%b %Y")

    try:
        hashed_password = _password_hasher.hash(password)
        # write login record first; rely on conditional write to prevent races
        _login_tbl.put_item(
            Item={
                "username": username,
                "password": hashed_password,
                "user_id": user_id,
            },
            ConditionExpression="attribute_not_exists(username)",
        )
        _user_tbl.put_item(
            Item={
                "email": email,
                "username": username,
                "user_id": user_id,
                "first_name": first_name,
                "last_name": last_name,
                "join_date": current_date,
            }
        )
        return {"status": "success", "message": "User added successfully"}
    except ClientError as e:
        # check specific conditional failure to return friendlier message
        err_code = e.response.get("Error", {}).get("Code", "")
        if err_code == "ConditionalCheckFailedException":
            return {"status": "error", "message": "Username already taken"}
        _log("add_user client error:", e)
        return {"status": "error", "message": f"Database Error: {str(e)}"}
    except Exception as e:  # pylint: disable=broad-exception-caught
        _log("add_user unexpected error:", e)
        return {"status": "error", "message": "User creation failed"}


def is_email_available(email):
    """Return True if the email is unused (False on any DB error to be conservative)."""
    try:
        response = _user_tbl.query(KeyConditionExpression=Key("email").eq(email))
        return response.get("Count", 0) == 0
    except (ClientError, BotoCoreError, NoCredentialsError) as e:
        _log("is_email_available DB error:", e)
        return False
    except Exception as e:  # pylint: disable=broad-exception-caught
        _log("is_email_available unexpected:", e)
        return False


def get_user_details(username):
    """Fetch user profile info by username via a GSI called UsernameIndex."""
    try:
        response = _user_tbl.query(
            IndexName="UsernameIndex",
            KeyConditionExpression=Key("username").eq(username),
        )
        if response.get("Count", 0) > 0:
            item = response["Items"][0]
            full = f"{item.get('first_name','')} {item.get('last_name','')}".strip()
            return {
                "name": full if full else username,
                "email": item.get("email", "N/A"),
                "join_date": item.get("join_date", "N/A"),
            }
        return None
    except (ClientError, BotoCoreError, NoCredentialsError) as e:
        _log("get_user_details DB error:", e)
        return None
    except Exception as e:  # pylint: disable=broad-exception-caught
        _log("get_user_details unexpected:", e)
        return None


def reset_password(username, email, new_password):
    """
    Reset user password.
    NOTE: This flow is insecure in production — should be replaced with OTP / email flow.
    """
    try:
        user_check = _user_tbl.query(
            IndexName="UsernameIndex",
            KeyConditionExpression=Key("username").eq(username),
        )
        if not user_check.get("Items") or user_check["Items"][0].get("email") != email:
            return {"status": "error", "message": "Invalid username/email"}

        hashed = _password_hasher.hash(new_password)
        _login_tbl.update_item(
            Key={"username": username},
            UpdateExpression="set password=:p",
            ExpressionAttributeValues={":p": hashed},
        )
        return {"status": "success"}
    except (ClientError, BotoCoreError, NoCredentialsError) as e:
        _log("reset_password DB error:", e)
        return {"status": "error", "message": str(e)}
    except Exception as e:  # pylint: disable=broad-exception-caught
        _log("reset_password unexpected:", e)
        return {"status": "error", "message": "Password reset failed"}


def update_password(username, current, new_p):
    """Change password after verifying current password."""
    login = login_user(username, current)
    if login.get("status") != "success":
        return login

    if current == new_p:
        return {"status": "error", "message": "New password cannot be same as current"}

    try:
        hashed = _password_hasher.hash(new_p)
        _login_tbl.update_item(
            Key={"username": username},
            UpdateExpression="set password=:p",
            ExpressionAttributeValues={":p": hashed},
        )
        return {"status": "success"}
    except (ClientError, BotoCoreError, NoCredentialsError) as e:
        _log("update_password DB error:", e)
        return {"status": "error", "message": str(e)}
    except Exception as e:  # pylint: disable=broad-exception-caught
        _log("update_password unexpected:", e)
        return {"status": "error", "message": "Password update failed"}


def add_transaction_db(username, tx_data):
    """Add a new portfolio transaction record for a user."""
    # human note: using epoch ms as tx id for simplicity and sortability
    tx_id = str(int(time.time() * 1000))
    symbol = safe_str(tx_data.get("symbol"), "UNK")
    tx_type = safe_str(tx_data.get("type"), "buy").lower()
    amount_dec = to_decimal(tx_data.get("amount", 0))
    price_dec = to_decimal(tx_data.get("price", 0))

    # if it's a sell, validate that the resulting balance stays non-negative
    if tx_type == "sell":
        try:
            # note: supply negative amount to indicate removal from holdings
            validate_ledger_impact(username, symbol, -float(amount_dec))
        except ValueError as e:
            return {"error": str(e)}

    item = {
        "username": username,
        "tx_id": tx_id,
        "type": tx_type,
        "coin": safe_str(tx_data.get("coin"), "Unknown"),
        "symbol": symbol,
        # store as strings in DB to avoid Decimal serialization issues with boto/dynamodb
        "amount": str(amount_dec),
        "price": str(price_dec),
        "date": safe_str(tx_data.get("date")),
    }

    try:
        _portfolio_tbl.put_item(Item=item)
        # return a client-friendly object with an 'id' field
        return {**item, "id": tx_id}
    except (ClientError, BotoCoreError, NoCredentialsError) as e:
        _log("add_transaction_db DB error:", e)
        return {"error": str(e)}
    except Exception as e:  # pylint: disable=broad-exception-caught
        _log("add_transaction_db unexpected:", e)
        return {"error": "Failed to add transaction"}


def get_transactions_db(username):
    """Fetch all transactions for a user and normalize numeric fields."""
    try:
        response = _portfolio_tbl.query(
            KeyConditionExpression=Key("username").eq(username)
        )
        items = response.get("Items", []) if isinstance(response, dict) else []
        cleaned_items = []

        for i in items:
            # human-style cautious parsing with small redundancy
            try:
                amount_val = float(i.get("amount", 0))
            except Exception:  # pylint: disable=broad-exception-caught
                amount_val = 0.0

            try:
                price_val = float(i.get("price", 0))
            except Exception:  # pylint: disable=broad-exception-caught
                price_val = 0.0

            cleaned_items.append(
                {
                    "id": i.get("tx_id"),
                    "type": i.get("type"),
                    "coin": i.get("coin"),
                    "symbol": i.get("symbol"),
                    "amount": amount_val,
                    "price": price_val,
                    "date": i.get("date"),
                }
            )
        return cleaned_items
    except (ClientError, BotoCoreError, NoCredentialsError) as e:
        _log("get_transactions_db DB error:", e)
        return []
    except Exception as e:  # pylint: disable=broad-exception-caught
        _log("get_transactions_db unexpected:", e)
        return []


def update_transaction_db(username, tx_data):
    """Update an existing transaction. tx_data must include 'id'."""
    if "id" not in tx_data:
        return {"error": "Transaction ID missing"}

    try:
        old_tx_resp = _portfolio_tbl.get_item(
            Key={"username": username, "tx_id": str(tx_data["id"])}
        )
        if "Item" not in old_tx_resp:
            return {"error": "Transaction not found"}
        old_tx = old_tx_resp["Item"]

        symbol = old_tx.get("symbol")
        new_amount = float(tx_data["amount"])
        new_type = tx_data["type"]
        old_amount = float(old_tx.get("amount"))
        old_type = old_tx.get("type")

        net_change = 0.0
        # This logic attempts to compute the delta effect on holdings
        if old_type == "buy":
            net_change -= old_amount
        else:
            net_change += old_amount

        if new_type == "buy":
            net_change += new_amount
        else:
            net_change -= new_amount

        try:
            validate_ledger_impact(username, symbol, net_change)
        except ValueError as e:
            return {"error": str(e)}

        # perform the atomic update
        _portfolio_tbl.update_item(
            Key={"username": username, "tx_id": str(tx_data["id"])},
            UpdateExpression="set amount=:a, price=:p, coin=:c, #d=:d, #t=:t",
            ExpressionAttributeNames={"#d": "date", "#t": "type"},
            ExpressionAttributeValues={
                ":a": str(new_amount),
                ":p": str(tx_data["price"]),
                ":c": safe_str(tx_data.get("coin"), old_tx.get("coin")),
                ":d": tx_data["date"],
                ":t": new_type,
            },
        )
        return {"status": "success"}
    except (ClientError, BotoCoreError, NoCredentialsError) as e:
        _log("update_transaction_db DB error:", e)
        return {"error": str(e)}
    except Exception as e:  # pylint: disable=broad-exception-caught
        _log("update_transaction_db unexpected:", e)
        return {"error": "Failed to update transaction"}


def delete_transaction_db(username, tx_id):
    """Delete a transaction after validating its ledger impact."""
    try:
        old_tx_resp = _portfolio_tbl.get_item(
            Key={"username": username, "tx_id": str(tx_id)}
        )
        if "Item" not in old_tx_resp:
            return {"error": "Transaction not found"}
        old_tx = old_tx_resp["Item"]

        # compute the ledger impact of removing this transaction
        impact = Decimal("0.0")
        amount = to_decimal(old_tx.get("amount", 0))

        if old_tx.get("type") == "buy":
            impact = -amount
        else:
            impact = amount

        try:
            validate_ledger_impact(username, old_tx.get("symbol"), impact)
        except ValueError as e:
            return {"error": str(e)}

        _portfolio_tbl.delete_item(Key={"username": username, "tx_id": str(tx_id)})
        return {"status": "success"}
    except (ClientError, BotoCoreError, NoCredentialsError) as e:
        _log("delete_transaction_db DB error:", e)
        return {"status": "error", "message": str(e)}
    except Exception as e:  # pylint: disable=broad-exception-caught
        _log("delete_transaction_db unexpected:", e)
        return {"status": "error", "message": "Failed to delete transaction"}


def update_user_details(username, data):
    """
    Update profile details for a user.
    Note: DynamoDB schema uses email as the partition key in user_details table, so changing email
    requires a transactional delete + put to effectively rename the key.
    """
    current_user = get_user_details(username)
    if not current_user:
        return {"error": "User not found"}

    current_email = current_user.get("email")
    new_email = (
        data.get("email", current_email).strip() if data.get("email") else current_email
    )
    first_name, last_name = split_name(data.get("name", current_user.get("name", "")))

    try:
        if new_email != current_email:
            # fetch the existing item to reconstruct it with new email
            old_item_resp = _user_tbl.query(
                IndexName="UsernameIndex",
                KeyConditionExpression=Key("username").eq(username),
            )
            if not old_item_resp.get("Items"):
                return {"error": "User record not found"}
            old_item = old_item_resp["Items"][0]

            # build new item and use a transactional write to atomically replace the key
            new_item = old_item.copy()
            new_item["email"] = new_email
            new_item["first_name"] = first_name
            new_item["last_name"] = last_name

            # human note: dynamodb.transact_write_items expects a specific structure
            _dynamo.meta.client.transact_write_items(
                TransactItems=[
                    {
                        "Delete": {
                            "TableName": "user_details",
                            "Key": {"email": current_email, "username": username},
                        }
                    },
                    {
                        "Put": {
                            "TableName": "user_details",
                            "Item": new_item,
                            "ConditionExpression": "attribute_not_exists(email)",
                        }
                    },
                ]
            )
            return {"status": "success", "message": "Profile and Email updated"}

        # otherwise just update the name fields in place
        _user_tbl.update_item(
            Key={"email": current_email, "username": username},
            UpdateExpression="set first_name=:f, last_name=:l",
            ExpressionAttributeValues={":f": first_name, ":l": last_name},
        )
        return {"status": "success", "message": "Profile updated successfully"}
    except (ClientError, BotoCoreError, NoCredentialsError) as e:
        _log("update_user_details DB error:", e)
        return {"error": f"Update failed: {str(e)}"}
    except Exception as e:  # pylint: disable=broad-exception-caught
        _log("update_user_details unexpected:", e)
        return {"error": "Failed to update profile"}
