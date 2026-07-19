"""
Unit tests for the DynamoDB Table Management Module.
"""

import sys
import os
from unittest.mock import MagicMock
import pytest
from botocore.exceptions import ClientError

# Add parent directory to path so imports resolve correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.table import SafeTableWrapper


class TestSafeTableWrapper:
    def test_getattr_delegates_to_underlying_table(self, mocker):
        """Test that attribute access is delegated to the underlying boto3 Table object."""
        mock_dynamo = mocker.patch("database.table._DYNAMODB")
        mock_table = MagicMock()
        mock_dynamo.Table.return_value = mock_table

        # Setup the wrapper
        wrapper = SafeTableWrapper("test_table", lambda x: None)

        # Access an attribute (e.g., put_item)
        _ = wrapper.put_item

        # Verify underlying table was accessed
        assert getattr(wrapper, "_table") == mock_table

    def test_method_call_success(self, mocker):
        """Test that a method call works normally when no error occurs."""
        mock_dynamo = mocker.patch("database.table._DYNAMODB")
        mock_table = MagicMock()
        mock_dynamo.Table.return_value = mock_table

        # Mock successful response
        mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

        wrapper = SafeTableWrapper("test_table", lambda x: None)
        response = wrapper.put_item(Item={"id": "1"})

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        mock_table.put_item.assert_called_once()

    def test_method_call_recreates_table_on_resource_not_found(self, mocker):
        """
        Test that if a method raises ResourceNotFoundException,
        the wrapper calls the creation function and retries.
        """
        mock_dynamo = mocker.patch("database.table._DYNAMODB")

        # Create a mock for the initial (missing) table and the new (recreated) table
        mock_missing_table = MagicMock()
        mock_new_table = MagicMock()

        # The first call to _DYNAMODB.Table returns the missing table
        mock_dynamo.Table.return_value = mock_missing_table

        # Define the creation function mock
        mock_create_func = MagicMock(return_value=mock_new_table)

        # Setup the exception
        error_response = {
            "Error": {"Code": "ResourceNotFoundException", "Message": "Not Found"}
        }
        client_error = ClientError(error_response, "PutItem")

        # The first call raises error, the second (retry) succeeds
        mock_missing_table.put_item.side_effect = client_error
        mock_new_table.put_item.return_value = "Success"

        # Initialize wrapper
        wrapper = SafeTableWrapper("test_table", mock_create_func)

        # Act
        result = wrapper.put_item(Item={"key": "val"})

        # Assert
        # 1. The creation function was called with the table name
        mock_create_func.assert_called_once_with("test_table")

        # 2. The result matches the retry's return value
        assert result == "Success"

        # 3. The internal table reference should now be the new table (returned by create_func)
        assert wrapper._table == mock_new_table

    def test_method_call_raises_other_client_errors(self, mocker):
        """Test that non-ResourceNotFound exceptions are re-raised immediately."""
        mock_dynamo = mocker.patch("database.table._DYNAMODB")
        mock_table = MagicMock()
        mock_dynamo.Table.return_value = mock_table

        # Different error code
        error_response = {"Error": {"Code": "ProvisionedThroughputExceededException"}}
        client_error = ClientError(error_response, "PutItem")
        mock_table.put_item.side_effect = client_error

        wrapper = SafeTableWrapper("test_table", lambda x: None)

        with pytest.raises(ClientError) as excinfo:
            wrapper.put_item(Item={"key": "val"})

        assert (
            excinfo.value.response["Error"]["Code"]
            == "ProvisionedThroughputExceededException"
        )

    def test_recreation_failure_raises_original_exception(self, mocker):
        """
        Test that if recreation fails (e.g. creation function raises error),
        the original ResourceNotFoundException is raised.
        """
        mock_dynamo = mocker.patch("database.table._DYNAMODB")
        mock_table = MagicMock()
        mock_dynamo.Table.return_value = mock_table

        error_response = {"Error": {"Code": "ResourceNotFoundException"}}
        client_error = ClientError(error_response, "PutItem")
        mock_table.put_item.side_effect = client_error

        # Creation function that fails
        mock_create_func = MagicMock(side_effect=Exception("Creation failed"))

        wrapper = SafeTableWrapper("test_table", mock_create_func)

        with pytest.raises(ClientError) as excinfo:
            wrapper.put_item(Item={"key": "val"})

        assert excinfo.value.response["Error"]["Code"] == "ResourceNotFoundException"
