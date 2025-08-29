#!/usr/bin/env python3
"""
Send Telegram digests for any recent inbound emails that have not yet been
notified. This acts as a safety net if webhooks lag or miss a push.
"""
from __future__ import annotations
import os
import pathlib
from dotenv import load_dotenv

# Load secrets
load_dotenv('/etc/pa_v2/secrets.env')

# Path setup
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from services.email.email_repo import EmailRepo
from interfaces.telegram.views.digest import build_digest
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def main(hours: int = 24, batch: int = 20) -> int:
    repo = EmailRepo()

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram not configured; aborting notify_pending")
        return 0

    unnotified = repo.list_recent_unnotified(since_hours=hours, limit=batch)
    if not unnotified:
        print("📭 No unnotified emails found")
        return 0

    # Convert to digest row tuples expected by send_digest
    rows = []
    for e in unnotified:
        rows.append((
            e["id"], e["provider"], e.get("from_display"), e.get("from_email"),
            e.get("subject"), e.get("snippet"), e.get("received_at")
        ))

    # Build digest content and send via HTTP API to avoid async issues
    text, markup, mode = build_digest(rows)
    # Convert InlineKeyboardMarkup to dict format for JSON
    keyboard_data = []
    for row in getattr(markup, 'inline_keyboard', []) or []:
        button_row = []
        for button in row:
            button_row.append({
                "text": button.text,
                "callback_data": button.callback_data
            })
        keyboard_data.append(button_row)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": int(TELEGRAM_CHAT_ID),
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": {"inline_keyboard": keyboard_data}
    }

    sent = 0
    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            sent = len(rows)
            print(f"✅ Sent digest for {sent} pending emails")
        else:
            print(f"❌ Telegram API error: {resp.status_code} {resp.text}")
            return 0
    except Exception as ex:
        print(f"❌ Failed to send digest: {ex}")
        return 0

    # Mark as notified to prevent duplicates
    for e in unnotified:
        try:
            repo.mark_notified(e["id"])
        except Exception as ex:
            print(f"⚠️ Failed to mark email {e['id']} as notified: {ex}")

    return sent


if __name__ == "__main__":
    main()
