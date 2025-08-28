"""Simple PostgreSQL connection helper."""
from __future__ import annotations

import os
import psycopg
from typing import Any


def get_conn() -> psycopg.Connection[Any]:
    """Return a new database connection.

    The connection parameters are read from the ``DATABASE_URL`` environment
    variable. This helper centralizes access so modules can share the same
    configuration without repeating boilerplate.
    """
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL environment variable is required")
    return psycopg.connect(dsn)
