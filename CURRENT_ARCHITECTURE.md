# PA_V2 - Current Architecture (Post-Cleanup)

## System Overview

PA_V2 now operates as a **webhook-based email processing system** with the following components:

### Active Components ✅

#### 1. **Gmail Webhook System**
- **Location**: `src/webhooks/app.py`, `src/webhooks/svc.py`
- **Purpose**: Receives Gmail push notifications in real-time
- **Service**: `systemd/pa-webhook-api.service`
- **Process**: Gmail → Google Cloud Pub/Sub → Webhook → Database → Telegram

#### 2. **Gmail Watch Management**
- **Location**: `src/jobs/push_lifecycle.py`, `tools/setup_gmail_push.py`
- **Purpose**: Manages Gmail push notification subscriptions
- **Service**: `systemd/pa-gmail-watch.service` + `systemd/pa-gmail-watch.timer`

#### 3. **Outlook Provider (On-Demand)**
- **Location**: `src/services/email/providers/outlook_provider.py`, `src/providers/outlook_*.py`
- **Purpose**: Send emails, delete emails, filter emails, get contacts
- **Usage**: Manual/filtered operations only - NO automatic polling

#### 4. **Database Storage**
- **Location**: `src/services/email/email_repo.py`
- **Purpose**: Store all emails with threading information
- **Features**: Internet Message-ID tracking, cross-provider threading

#### 5. **Telegram Integration**
- **Location**: `src/interfaces/telegram/`, `src/webhooks/svc.py`
- **Purpose**: Send notifications with AI summaries and draft replies
- **Service**: `systemd/pa-telegram-bot.service`

### Email Flow

```
BYU Outlook Email → Forwarded to Gmail (label: BYU_ASC59)
                                      ↓
Gmail Push Notification → Google Cloud Pub/Sub
                                      ↓
PA_V2 Webhook API → Process & Store → Telegram Notification
```

### Removed Components ❌

The following polling-based components have been **REMOVED**:

- ❌ `src/jobs/email_check.py` - Old polling job
- ❌ `src/services/email/jobs/monitor.py` - Email monitoring job
- ❌ `src/services/email/jobs/retention_cleanup.py` - Retention cleanup
- ❌ `systemd/pa-email-check.service` - Email check service
- ❌ `systemd/pa-email-check*.timer` - Email check timers
- ❌ `systemd/pa-email-retention.*` - Retention services
- ❌ Automatic Outlook polling functionality
- ❌ Timer-based BYU email retrieval

### Safety Net Components 🛡️

These components remain as backup/safety mechanisms:

- ✅ `src/jobs/notify_pending.py` - Retry failed notifications
- ✅ `src/jobs/retry_notifications.py` - Safety net for webhook failures

## Benefits of Current Architecture

1. **Real-time Processing**: Webhooks provide instant email notifications
2. **No Duplication**: BYU emails are processed once via Gmail redirect
3. **Efficient**: No unnecessary polling or timer overhead
4. **Reliable**: Gmail webhook + safety net scripts ensure no missed emails
5. **Flexible**: On-demand Outlook operations for filtering/management

## Deployment

Use the webhook-only deployment:
```bash
./deploy_webhook_only.sh
```

Or the Internet Message-ID enhanced deployment:
```bash
./deploy_internet_message_id.sh
```

## Manual Operations

For manual email operations (filtering, etc.):
```python
# Get emails from Outlook using filters
from services.email.providers.outlook_provider import OutlookGraphProvider
outlook = OutlookGraphProvider()
emails = outlook.get_latest_emails(count=10)

# Send email via Outlook
outlook.send_email(to="user@example.com", subject="Test", body="Hello")
```
