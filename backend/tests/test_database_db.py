"""Unit tests for database connection module."""

import sys
import os
import pytest
from moto import mock_aws

# FIX: Add parent directory to path so imports resolve correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the module to be tested using absolute import
# pylint: disable=wrong-import-position
from database.db import db_resource


# Mock the DynamoDB resource creation and credential logic
@mock_aws
def test_create_db_resource_with_credentials(mocker):
    """
    Test that db_resource correctly initializes DynamoDB
    when all required environment variables are set.
    """
    # Mock os.getenv to return mock credentials and region
    mocker.patch(
        "os.getenv",
        side_effect={
            "AWS_ACCESS_KEY_ID": "test_access_key",
            "AWS_SECRET_ACCESS_KEY": "test_secret_key",
            "AWS_REGION_NAME": "us-east-1",
        }.get,
    )

    # Calling the function should not raise an error
    resource = db_resource()

    assert resource is not None
    assert resource.meta.client.meta.region_name == "us-east-1"
