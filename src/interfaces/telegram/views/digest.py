# src/interfaces/telegram/views/digest.py
import os
import sys
import pathlib
from typing import Iterable, Tuple
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode

# Add src to path for imports
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from services.email.email_repo import EmailRepo

REPO = EmailRepo()

# Provider icons (keep your preferred style)
PROVIDER_ICON = {
    "gmail":   "✉️🟥",
    "outlook": "✉️🟦",
}

# -----------------------
#  Badge classification
# -----------------------
# hard rules you asked for:
#   • BYU_ASC59 label  -> 🎓
#   • any message TO your personal Gmail -> 🏠
# optional business rule (💼), easy to toggle by env:
PERSONAL_TO_EMAIL = os.getenv("PERSONAL_TO_EMAIL", "adrianosancarneiro@gmail.com").lower()
BYU_LABEL = os.getenv("BYU_LABEL", "BYU_ASC59")
BUSINESS_EMAIL = os.getenv("BUSINESS_EMAIL", "adriano@mentorius.app").lower()     # optional
BUSINESS_DOMAIN = os.getenv("BUSINESS_DOMAIN", "mentorius.app").lower()           # optional

def _lower_list(xs):
    return [x.lower() for x in xs or []]

def _any_address_matches(addresses, target_email, target_domain=None):
    for a in _lower_list(addresses):
        if target_email and a == target_email:
            return True
        if target_domain and a.endswith(f"@{target_domain}"):
            return True
    return False

def _classify_badge(from_email: str, to_emails, cc_emails, bcc_emails, tags) -> str:
    """Return one of: '🎓', '🏠', '💼' (if business applies), in that priority order."""

    # 1) School/edu hard rule: BYU label present
    if BYU_LABEL in (tags or []):
        return "🎓"

    # (Optional) Business: if any party involves your business mailbox/domain
    #   Note: put business before personal-to so outbound/customer messages get 💼
    all_parties = []
    if from_email: all_parties.append(from_email)
    all_parties.extend(to_emails or [])
    all_parties.extend(cc_emails or [])
    all_parties.extend(bcc_emails or [])
    if _any_address_matches(all_parties, BUSINESS_EMAIL, BUSINESS_DOMAIN):
        return "💼"

    # 2) Personal hard rule: anything addressed TO your personal Gmail
    if _any_address_matches(to_emails or [], PERSONAL_TO_EMAIL):
        return "🏠"

    # 3) Default: treat as personal if nothing else matched (your request kept logic simple)
    return "🏠"

# -----------------------
#  Row rendering
# -----------------------
def row_text(provider: str, sender: str, subject: str, snippet: str, badges: str = "") -> str:
    prov = PROVIDER_ICON.get(provider, "✉️")
    s_sender = sender or "(unknown)"
    s_subject = subject or "(no subject)"
    s_snip = (snippet or "").replace("\n", " ").strip()
    if len(s_snip) > 140:
        s_snip = s_snip[:137] + "…"
    return f"{badges}{prov} *{s_sender}*\n_{s_subject}_\n{s_snip}"

def build_digest(rows: Iterable[tuple]) -> Tuple[str, InlineKeyboardMarkup, str]:
    """
    rows: (email_id, provider, from_display, from_email, subject, snippet, received_at)
    returns: (text, markup, ParseMode)
    """
    text_lines = []
    keyboard_rows = []

    for (email_id, provider, from_display, from_email, subject, snippet, _rcvd) in rows:
        # Pull richer fields so we can classify
        detail = REPO.get_email_detail(email_id)  # must include tags, to_emails, cc_emails, bcc_emails
        tags      = detail.get("tags") or []
        to_emails = detail.get("to_emails")  or []
        cc_emails = detail.get("cc_emails")  or []
        bcc_emails= detail.get("bcc_emails") or []

        badge = _classify_badge(from_email or detail.get("from_email"),
                                to_emails, cc_emails, bcc_emails, tags)
        badges = f"{badge} "

        text_lines.append(row_text(provider, from_display or from_email, subject, snippet, badges=badges))

        keyboard_rows.append([
            InlineKeyboardButton("🔎 More",  callback_data=f"more:{email_id}"),
            InlineKeyboardButton("✍️ Reply", callback_data=f"reply:{email_id}"),
            InlineKeyboardButton("⭐",       callback_data=f"star:{email_id}"),
            InlineKeyboardButton("🗑",       callback_data=f"delreq:{email_id}"),
        ])

    digest_text = "\n\n".join(text_lines) if text_lines else "No new emails."
    return digest_text, InlineKeyboardMarkup(keyboard_rows), ParseMode.MARKDOWN

def send_digest(bot, chat_id: int, rows: Iterable[tuple]):
    text, markup, mode = build_digest(rows)
    return bot.send_message(chat_id=chat_id, text=text, reply_markup=markup, parse_mode=mode)
