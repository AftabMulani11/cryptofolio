"""
Database Connection Module.

This module handles the initialization of the DynamoDB resource.
It facilitates switching between a local DynamoDB instance (often used
for development) and the live AWS service based on the presence of
environment variables.
"""

import os
import boto3


def db_resource():
    """
    Initialize and return a DynamoDB resource.

    The function inspects the environment for AWS credentials. If valid credentials
    are found, it connects to the AWS DynamoDB service. If they are missing,
    it defaults to a local DynamoDB instance running on localhost:8000.

    Returns:
        boto3.resource: A configured DynamoDB resource object.
    """
    # Check if AWS credentials are provided in the environment.
    if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
        dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION_NAME"))

    return dynamodb
