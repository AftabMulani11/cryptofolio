"""
Unit tests for application configuration.
"""

import sys
import os
import importlib
import pytest
from unittest.mock import patch

# Fix path to ensure we can import 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_app_raises_error_missing_secret():
    """Test that app raises ValueError if token_secret_key is missing."""
    # Remove app from sys.modules to force a fresh import
    if "app" in sys.modules:
        del sys.modules["app"]

    # Mock environment to have NO secrets (clear=True removes all env vars temporarily)
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as excinfo:
            import app  # pylint: disable=import-outside-toplevel

            importlib.reload(app)

        assert "CRITICAL: 'token_secret_key' env variable is not set" in str(
            excinfo.value
        )

    # Restore environment for other tests by reloading app with correct env
    os.environ["token_secret_key"] = "test-secret"
    # We re-import app safely to ensure it doesn't break subsequent tests
    if "app" in sys.modules:
        import app  # pylint: disable=import-outside-toplevel

        importlib.reload(app)
