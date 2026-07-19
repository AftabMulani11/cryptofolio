"""
Unit tests for the Worker module.
"""

import sys
import os
from unittest.mock import MagicMock, call
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the module under test
import worker


class TestWorker:

    @pytest.fixture
    def mock_ws(self, mocker):
        """Mock the crypto.binance_ws module."""
        return mocker.patch("worker.binance_ws")

    @pytest.fixture
    def mock_sleep(self, mocker):
        """Mock time.sleep to avoid waiting during tests."""
        return mocker.patch("time.sleep")

    def test_start_once(self, mock_ws):
        """Test that _start_once calls the websocket runner."""
        worker._start_once()
        mock_ws.run_ws.assert_called_once()

    def test_start_with_retries_success(self, mock_ws, mock_sleep):
        """Test that the loop exits immediately if _start_once returns normally."""
        # Setup: run_ws returns None (success) immediately
        mock_ws.run_ws.return_value = None

        worker._start_with_retries(max_retries=3)

        # Should call run_ws once and not sleep
        mock_ws.run_ws.assert_called_once()
        mock_sleep.assert_not_called()

    def test_start_with_retries_failure_and_retry(self, mock_ws, mock_sleep):
        """Test that it retries upon exception."""
        # Setup: run_ws fails twice, then succeeds
        mock_ws.run_ws.side_effect = [Exception("Crash 1"), Exception("Crash 2"), None]

        worker._start_with_retries(max_retries=5)

        # Should have called run_ws 3 times
        assert mock_ws.run_ws.call_count == 3
        # Should have slept twice (backoff)
        assert mock_sleep.call_count == 2

    def test_start_with_retries_max_limit(self, mock_ws, mock_sleep):
        """Test that it gives up after max_retries."""
        # Setup: run_ws always fails
        mock_ws.run_ws.side_effect = Exception("Persistent Crash")

        with pytest.raises(Exception) as excinfo:
            worker._start_with_retries(max_retries=2)

        assert "Persistent Crash" in str(excinfo.value)
        assert mock_ws.run_ws.call_count == 2

    def test_exponential_backoff_logic(self, mock_ws, mock_sleep):
        """Test that the sleep delay doubles (exponential backoff)."""
        # Setup: Fail 3 times
        mock_ws.run_ws.side_effect = [
            Exception("E1"),
            Exception("E2"),
            Exception("E3"),
            None,
        ]

        worker._start_with_retries(max_retries=5, initial_delay=1)

        # Check sleep calls.
        # Attempt 1 fail -> sleep(1) -> delay becomes 2
        # Attempt 2 fail -> sleep(2) -> delay becomes 4
        # Attempt 3 fail -> sleep(4)
        mock_sleep.assert_has_calls([call(1), call(2), call(4)])

    def test_keyboard_interrupt_exits_gracefully(self, mock_ws, mock_sleep):
        """Test that KeyboardInterrupt propagates up."""
        mock_ws.run_ws.side_effect = KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            worker._start_with_retries(max_retries=5)

        mock_sleep.assert_not_called()
