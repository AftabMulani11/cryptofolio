"""
DynamoDB Table Management Module.

This module provides utilities for managing DynamoDB tables, including
automatic creation of missing tables and a wrapper class for fault-tolerant
access during application startup.
"""

from botocore.exceptions import ClientError
from . import db as db_module

# Initialize the DynamoDB resource
_DYNAMODB = db_module.db_resource()


def _log(*parts):
    """
    Internal helper to print log messages with a specific prefix.
    """
    print("table_mgr>", *parts)


class SafeTableWrapper:  # pylint: disable=too-few-public-methods
    """
    A wrapper around a boto3 DynamoDB Table resource.

    This class intercepts attribute access to underlying table methods.
    If a method call fails because the table does not exist (ResourceNotFoundException),
    it attempts to recreate the table using the provided creation function
    and then retries the operation.
    """

    def __init__(self, table_name, creation_func):
        """
        Initialize the wrapper.

        Args:
            table_name (str): The name of the DynamoDB table.
            creation_func (callable): A function that creates the table if it is missing.
        """
        self.table_name = table_name
        self.create_func = creation_func
        self._table = _DYNAMODB.Table(table_name)

    def __getattr__(self, name):
        """
        Delegate attribute access to the underlying boto3 Table object.

        If the attribute is a callable (method), it is wrapped to handle
        ResourceNotFoundException by attempting to recreate the table.
        """
        attr = getattr(self._table, name)

        if callable(attr):

            def wrapper(*args, **kwargs):
                try:
                    return attr(*args, **kwargs)
                except ClientError as exc:
                    # Check if the error is due to a missing table
                    error_code = exc.response.get("Error", {}).get("Code", "")
                    if error_code == "ResourceNotFoundException":
                        _log(
                            f"Table {self.table_name} missing. Attempting to recreate..."
                        )
                        try:
                            # Recreate the table and update the internal reference
                            self._table = self.create_func(self.table_name)
                            _log(
                                f"Recreated table {self.table_name}. Retrying operation..."
                            )

                            # Retry the original operation on the new table instance
                            return getattr(self._table, name)(*args, **kwargs)
                        except Exception as create_exc:
                            _log(
                                f"Failed to recreate table {self.table_name}: {create_exc}"
                            )
                            # Explicitly raise from the creation exception
                            raise exc from create_exc
                    # Re-raise unrelated errors
                    raise exc

            return wrapper

        return attr


def get_table(table_name):
    """
    Retrieve a safe wrapper for a DynamoDB table.

    Args:
        table_name (str): The name of the table to retrieve.

    Returns:
        SafeTableWrapper: A wrapper that handles auto-creation if the table is missing.
    """
    return SafeTableWrapper(table_name, user_details_table)


def user_details_table(table_name):
    """
    Ensure the specified DynamoDB table exists, creating it if necessary.

    This function defines the schema for 'user_details', 'login_details',
    and 'user_portfolio'.

    Args:
        table_name (str): The name of the table to create or retrieve.

    Returns:
        boto3.resources.factory.dynamodb.Table: The requested Table resource.

    Raises:
        ValueError: If the schema for the requested table name is not defined.
    """
    # Attempt to list existing tables to avoid redundant creation calls
    try:
        existing_tables_iter = _DYNAMODB.tables.all()
        existing_tables = [t.name for t in existing_tables_iter]
    except Exception as exc:  # pylint: disable=broad-exception-caught
        _log("Warning: failed to list tables:", exc)
        existing_tables = []

    if table_name in existing_tables:
        _log(f"Using existing DynamoDB table: {table_name}")
        return _DYNAMODB.Table(table_name)

    _log(f"Creating table '{table_name}'...")
    table = None

    # Define schemas for known tables
    if table_name == "user_details":
        table = _DYNAMODB.create_table(
            TableName="user_details",
            KeySchema=[
                {"AttributeName": "email", "KeyType": "HASH"},
                {"AttributeName": "username", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "email", "AttributeType": "S"},
                {"AttributeName": "username", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "UsernameIndex",
                    "KeySchema": [{"AttributeName": "username", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
    elif table_name == "login_details":
        table = _DYNAMODB.create_table(
            TableName="login_details",
            KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
    elif table_name == "user_portfolio":
        table = _DYNAMODB.create_table(
            TableName="user_portfolio",
            KeySchema=[
                {"AttributeName": "username", "KeyType": "HASH"},
                {"AttributeName": "tx_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "username", "AttributeType": "S"},
                {"AttributeName": "tx_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
    else:
        raise ValueError(f"Table definition for '{table_name}' not found.")

    # Block until the table status is active
    try:
        _log(f"Waiting for table '{table_name}' to become active...")
        table.meta.client.get_waiter("table_exists").wait(TableName=table_name)
        _log(f"Table '{table_name}' is ready.")
    except Exception as exc:
        _log(f"Error waiting for table '{table_name}':", exc)
        raise

    return table
