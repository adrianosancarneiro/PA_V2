import os
import sys
import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'src'))

pytest.importorskip('telegram')

from telegram.digest import build_digest, row_text


def test_row_text():
    """Test email row formatting"""
    result = row_text("gmail", "John Doe", "Test Subject", "This is a test snippet")
    assert "🟥" in result  # Gmail icon
    assert "*John Doe*" in result
    assert "_Test Subject_" in result
    assert "This is a test snippet" in result


def test_row_text_truncation():
    """Test snippet truncation"""
    long_snippet = "x" * 200
    result = row_text("outlook", "Test", "Subject", long_snippet)
    assert len(result) < 200
    assert "…" in result


def test_build_digest_empty():
    """Test digest with no emails"""
    text, markup, mode = build_digest([])
    assert text == "No new emails."
    assert markup.inline_keyboard == []


def test_build_digest_with_emails():
    """Test digest with sample emails"""
    rows = [
        (1, "gmail", "John Doe", "john@example.com", "Test Subject", "Test snippet", "2024-01-01"),
        (2, "outlook", "Jane Smith", "jane@example.com", "Another Subject", "Another snippet", "2024-01-02"),
    ]
    
    text, markup, mode = build_digest(rows)
    
    assert "John Doe" in text
    assert "Jane Smith" in text
    assert "Test Subject" in text
    assert "Another Subject" in text
    
    # Check buttons are created
    assert len(markup.inline_keyboard) == 2
    assert len(markup.inline_keyboard[0]) == 4  # More, Reply, Star, Delete buttons
    
    # Check callback data
    buttons = markup.inline_keyboard[0]
    assert buttons[0].callback_data == "more:1"
    assert buttons[1].callback_data == "reply:1"
    assert buttons[2].callback_data == "star:1"
    assert buttons[3].callback_data == "delreq:1"
