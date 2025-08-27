import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from email_system.filtering import filter_emails

SAMPLE_EMAILS = [
    {
        "subject": "Project update",
        "body_preview": "The project is on track",
        "from": "alice@example.com",
        "received_date": "2024-03-01T10:00:00",
    },
    {
        "subject": "Meeting notes",
        "body_preview": "Discussed project and timeline",
        "from": "bob@example.com",
        "received_date": "2024-03-05T12:00:00",
    },
]


def test_keyword_filter_subject():
    res = filter_emails(SAMPLE_EMAILS, keyword="meeting", fields=["subject"])
    assert len(res) == 1
    assert res[0]["subject"] == "Meeting notes"


def test_date_range_filter():
    res = filter_emails(
        SAMPLE_EMAILS,
        date_from="2024-03-02",
        date_to="2024-03-06",
    )
    assert len(res) == 1
    assert res[0]["from"] == "bob@example.com"


def test_sender_filter():
    res = filter_emails(SAMPLE_EMAILS, sender="alice")
    assert len(res) == 1
    assert res[0]["from"] == "alice@example.com"
