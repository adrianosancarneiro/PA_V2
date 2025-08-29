"""
Telegram digest module for PA_V2
Creates compact digest messages with inline action buttons
"""
from typing import Iterable, Tuple
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode

PROVIDER_ICON = {
    "gmail": "🟥",
    "outlook": "🟦",
}

def row_text(provider: str, sender: str, subject: str, snippet: str) -> str:
    """Format a single email row for the digest"""
    prov = PROVIDER_ICON.get(provider, "✉️")
    s_sender = sender or "(unknown)"
    s_subject = subject or "(no subject)"
    s_snip = (snippet or "").replace("\n", " ").strip()
    # keep snippet short-ish (1–2 lines)
    if len(s_snip) > 140:
        s_snip = s_snip[:137] + "…"
    return f"{prov} *{s_sender}*\n_{s_subject}_\n{s_snip}"

def build_digest(rows: Iterable[tuple]) -> Tuple[str, InlineKeyboardMarkup, str]:
    """
    Build digest message from email rows
    
    Args:
        rows: iterable of (email_id, provider, from_display, from_email, subject, snippet, received_at)
    
    Returns:
        tuple: (text, markup, ParseMode)
    """
    text_lines = []
    keyboard_rows = []
    
    for (email_id, provider, from_display, _from_email, subject, snippet, _rcvd) in rows:
        text_lines.append(row_text(provider, from_display, subject, snippet))
        keyboard_rows.append([
            InlineKeyboardButton("🔎 More", callback_data=f"more:{email_id}"),
            InlineKeyboardButton("✍️ Reply", callback_data=f"reply:{email_id}"),
            InlineKeyboardButton("⭐", callback_data=f"star:{email_id}"),
            InlineKeyboardButton("🗑", callback_data=f"delreq:{email_id}"),
        ])
    
    digest_text = "\n\n".join(text_lines) if text_lines else "No new emails."
    return digest_text, InlineKeyboardMarkup(keyboard_rows), ParseMode.MARKDOWN

def send_digest(bot, chat_id: int, rows: Iterable[tuple]):
    """Send a digest message to Telegram"""
    text, markup, mode = build_digest(rows)
    return bot.send_message(chat_id=chat_id, text=text, reply_markup=markup, parse_mode=mode)
