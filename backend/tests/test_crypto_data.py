"""
Tests for crypto data text utilities.
"""

# File: backend/tests/test_crypto_data.py

from backend.crypto.crypto_data import _clean_html


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