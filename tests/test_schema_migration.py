import os
import sys
import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'src'))

pytest.importorskip('psycopg')

import psycopg


def test_tables_exist():
    dsn = os.environ.get('DATABASE_URL', 'postgresql://postgres@localhost/pa_v2_postgres_db')
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('email_threads','email_messages','email_drafts')
                ORDER BY table_name;
            """)
            rows = cur.fetchall()
            assert len(rows) == 3
