import os
import sys
import time
import pytest

# Ensure src is importable
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

pytest.importorskip("psycopg")

from repo.email_repo import EmailRepo


@pytest.fixture()
def repo():
    return EmailRepo()


def test_upsert_and_get_email(repo):
    ts = int(time.time())
    provider = 'gmail'
    provider_message_id = f'test_msg_py_{ts}'

    eid = repo.upsert_email(
        provider=provider,
        provider_message_id=provider_message_id,
        provider_thread_id=f'thread_{ts}',
        from_display='PyTest User',
        from_email='pytest@example.com',
        to_emails=['to@example.com'],
        cc_emails=[],
        bcc_emails=[],
        subject='PyTest Insertion',
        snippet='Snippet',
        body_plain='Plain body',
        body_html=None,
        received_at=None,
        tags=['pytest']
    )

    assert eid is not None

    # Duplicate insertion should not create a new row
    eid2 = repo.upsert_email(
        provider=provider,
        provider_message_id=provider_message_id,
        provider_thread_id=f'thread_{ts}',
        from_display='PyTest User',
        from_email='pytest@example.com',
        to_emails=['to@example.com'],
        cc_emails=[],
        bcc_emails=[],
        subject='Duplicate',
        snippet='Snippet',
        body_plain='Plain body',
        body_html=None,
        received_at=None,
        tags=['pytest']
    )

    assert eid == eid2


def test_retention_cleanup_returns_int(repo):
    res = repo.retention_cleanup('gmail', keep=10000)
    # The function should return an integer (deleted count) or None
    assert isinstance(res, (int, type(None)))
