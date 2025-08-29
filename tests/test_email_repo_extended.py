import os
import sys
import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'src'))

pytest.importorskip('psycopg')

from repo.email_repo import EmailRepo


@pytest.fixture
def repo():
    return EmailRepo()


def test_mark_important_method_exists(repo):
    """Test that mark_important method exists"""
    assert hasattr(repo, 'mark_important')
    assert callable(repo.mark_important)


def test_touch_method_exists(repo):
    """Test that touch method exists"""
    assert hasattr(repo, 'touch')
    assert callable(repo.touch)


def test_get_email_detail_method_exists(repo):
    """Test that get_email_detail method exists"""
    assert hasattr(repo, 'get_email_detail')
    assert callable(repo.get_email_detail)


def test_add_draft_method_exists(repo):
    """Test that add_draft method exists"""
    assert hasattr(repo, 'add_draft')
    assert callable(repo.add_draft)


def test_latest_new_messages_method_exists(repo):
    """Test that latest_new_messages method exists"""
    assert hasattr(repo, 'latest_new_messages')
    assert callable(repo.latest_new_messages)


def test_mark_thread_deleted_method_exists(repo):
    """Test that mark_thread_deleted method exists"""
    assert hasattr(repo, 'mark_thread_deleted')
    assert callable(repo.mark_thread_deleted)


def test_restore_thread_deleted_method_exists(repo):
    """Test that restore_thread_deleted method exists"""
    assert hasattr(repo, 'restore_thread_deleted')
    assert callable(repo.restore_thread_deleted)


def test_get_email_row_method_exists(repo):
    """Test that get_email_row method exists"""
    assert hasattr(repo, 'get_email_row')
    assert callable(repo.get_email_row)
