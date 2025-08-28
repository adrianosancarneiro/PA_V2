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
        # Fallback to constructing from individual env vars if DATABASE_URL not set
        host = os.environ.get("POSTGRES_HOST", "localhost")
        port = os.environ.get("POSTGRES_PORT", "5432") 
        user = os.environ.get("POSTGRES_USER", "postgres")
        database = os.environ.get("POSTGRES_DATABASE", "pa_v2_postgres_db")
        password = os.environ.get("POSTGRES_PASSWORD", "")
        
        if password:
            dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        else:
            dsn = f"postgresql://{user}@{host}:{port}/{database}"
    
    return psycopg.connect(dsn)
