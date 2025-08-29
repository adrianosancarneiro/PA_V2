#!/usr/bin/env python3
"""
Email retention cleanup job for PA_V2
Removes old emails keeping only the most recent 10,000 per provider
Run this periodically via cron or systemd timer to prevent unlimited growth
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load system-wide secrets
load_dotenv('/etc/pa_v2/secrets.env')

# Add src directory to path for imports
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from services.email.email_repo import EmailRepo

# Providers to clean up
PROVIDERS = ("gmail", "outlook")

# Number of emails to keep per provider (default: 10,000)
KEEP_COUNT = int(os.getenv("EMAIL_RETENTION_COUNT", "10000"))


def run_retention_cleanup():
    """Run email retention cleanup for all providers."""
    print(f"🧹 Starting email retention cleanup at {datetime.now()}")
    print(f"📊 Keeping {KEEP_COUNT} most recent emails per provider")
    
    repo = EmailRepo()
    total_deleted = 0
    
    for provider in PROVIDERS:
        try:
            deleted_count = repo.retention_cleanup(provider, keep=KEEP_COUNT)
            total_deleted += deleted_count
            print(f"✅ {provider}: Deleted {deleted_count} old emails")
        except Exception as e:
            print(f"❌ {provider}: Retention cleanup failed: {e}")
    
    print(f"🎯 Retention cleanup completed: {total_deleted} total emails deleted")
    return total_deleted


def main():
    """Main entry point for retention cleanup script."""
    try:
        deleted_count = run_retention_cleanup()
        print(f"✅ Retention cleanup successful: {deleted_count} emails removed")
    except Exception as e:
        print(f"❌ Retention cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
