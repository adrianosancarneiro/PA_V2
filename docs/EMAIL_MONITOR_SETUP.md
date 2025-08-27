# Email Monitoring System Setup Guide

This guide will help you set up an automated email monitoring system that checks Gmail and Outlook every minute and sends notifications to your Telegram bot with AI-generated summaries.

## 🏗️ Architecture Overview

The system consists of:
- **Email Checker Job** (`src/jobs/email_check.py`) - Monitors Gmail/Outlook for new emails
- **Systemd Service** - Runs the checker every minute as a background service  
- **Telegram Integration** - Sends notifications with AI summaries
- **LLaMA Integration** - Generates email summaries and draft replies

## 📋 Prerequisites

1. **Python 3.8+** with required packages
2. **Gmail/Outlook authentication** set up
3. **Telegram bot** created and configured
4. **LLaMA server** running (optional, for AI summaries)

## 🚀 Quick Setup

### 1. Set Environment Variables

```bash
# Telegram Configuration (Required)
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"

# LLaMA Configuration (Optional)
export LLAMA_BASE_URL="http://192.168.0.83:8080"

# Config Directory (Optional - defaults to ./config)
export CONFIG_DIR="/home/mentorius/AI_Services/PA_V2/config"
```

### 2. Setup Email Authentication

```bash
# Run the authentication setup
python3 -m src.main setup-auth

# Test authentication
python3 -m src.main check-emails
```

### 3. Install and Start the Service

```bash
# Run the installation script
./install_email_monitor.sh
```

That's it! The system will now check for emails every minute.

## 🔧 Manual Installation

If you prefer to install manually:

### 1. Copy Service Files

```bash
# Copy service file
sudo cp systemd/pa-email-check.service /etc/systemd/system/

# Copy timer file
sudo cp systemd/pa-email-check.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload
```

### 2. Configure Service File

Edit `/etc/systemd/system/pa-email-check.service` and update:
- `User=mentorius` (your username)
- `WorkingDirectory=/path/to/PA_V2`
- Environment variables

### 3. Enable and Start

```bash
# Enable timer (starts on boot)
sudo systemctl enable pa-email-check.timer

# Start timer now
sudo systemctl start pa-email-check.timer

# Check status
systemctl status pa-email-check.timer
```

## 📱 Telegram Bot Setup

### 1. Create a Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Save the bot token

### 2. Get Your Chat ID

```bash
# Method 1: Send a message to your bot, then check:
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates"

# Method 2: Message @userinfobot to get your user ID
```

## 🤖 LLaMA Server Setup (Optional)

The system can integrate with a local LLaMA server for AI summaries:

```bash
# Example: Start llama.cpp server
./llama-server --model your-model.gguf --host 0.0.0.0 --port 8080

# Test the server
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llama","messages":[{"role":"user","content":"Hello"}]}'
```

## 📊 Usage Commands

```bash
# Check emails once manually
python3 -m src.main check-emails

# Start continuous monitoring (interactive)
python3 -m src.main monitor-emails

# Check authentication status
python3 -m src.main list-providers

# Setup authentication
python3 -m src.main setup-auth
```

## 🛠️ Management Commands

### Service Management

```bash
# Check timer status
systemctl status pa-email-check.timer

# View recent logs
journalctl -u pa-email-check.service -n 50

# Follow logs in real-time
journalctl -u pa-email-check.service -f

# Stop the timer
sudo systemctl stop pa-email-check.timer

# Start the timer
sudo systemctl start pa-email-check.timer

# Disable (won't start on boot)
sudo systemctl disable pa-email-check.timer
```

### Change Check Frequency

#### Switch to Hourly Checks

```bash
# Stop current timer
sudo systemctl stop pa-email-check.timer

# Copy hourly timer
sudo cp systemd/pa-email-check-hourly.timer /etc/systemd/system/pa-email-check.timer

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl start pa-email-check.timer
```

#### Custom Frequency

Edit `/etc/systemd/system/pa-email-check.timer`:

```ini
[Timer]
# Every 5 minutes
OnCalendar=*:0/5

# Every 30 minutes  
OnCalendar=*:0,30

# Every hour at 15 minutes past
OnCalendar=*:15

# Daily at 9 AM
OnCalendar=09:00
```

## 🔍 Troubleshooting

### Check Email Authentication

```bash
# Test Gmail
python3 -c "
import sys; sys.path.insert(0, 'src')
from email_system.providers.gmail_provider import GmailProvider
gmail = GmailProvider()
print('Gmail auth:', gmail.is_authenticated())
"

# Test Outlook
python3 -c "
import sys; sys.path.insert(0, 'src')
from email_system.providers.outlook_provider import OutlookGraphProvider
outlook = OutlookGraphProvider()
print('Outlook auth:', outlook.is_authenticated())
"
```

### Check Telegram Configuration

```bash
# Test Telegram
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
  -d "chat_id=$TELEGRAM_CHAT_ID" \
  -d "text=Test message from PA_V2"
```

### Check LLaMA Server

```bash
# Test LLaMA endpoint
curl "$LLAMA_BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama","messages":[{"role":"user","content":"Hello"}],"temperature":0.7}'
```

### View State File

```bash
# Check what emails have been processed
cat config/email_check_state.json
```

### Reset State (Reprocess All Emails)

```bash
# Backup current state
cp config/email_check_state.json config/email_check_state.json.backup

# Remove state file to start fresh
rm config/email_check_state.json

# Next run will process recent emails again
```

## 📝 Configuration Files

### State File Location
- **Path**: `config/email_check_state.json`
- **Purpose**: Tracks last processed emails to avoid duplicates
- **Format**: JSON with timestamps and email IDs per provider

### Service Logs
- **Location**: `journalctl -u pa-email-check.service`
- **Retention**: Follows systemd journal settings
- **Levels**: Info, Warning, Error

## 🔒 Security Notes

1. **Environment Variables**: Store sensitive tokens in environment files, not in code
2. **File Permissions**: Ensure config files are readable only by your user
3. **Network**: LLaMA server should only be accessible locally
4. **Tokens**: Regularly rotate Telegram bot tokens

## 🎯 Customization

### Custom Email Filters

Edit `src/jobs/email_check.py` to add custom filtering:

```python
def should_process_email(email):
    """Add custom logic to filter emails"""
    subject = email.get('subject', '').lower()
    
    # Skip automated emails
    if any(word in subject for word in ['noreply', 'automated', 'newsletter']):
        return False
    
    # Only process important emails
    if any(word in subject for word in ['urgent', 'important', 'action required']):
        return True
    
    return True  # Process all others
```

### Custom AI Prompts

Modify the `llama_summarize_and_draft` function to change AI behavior:

```python
prompt = (
    "You are a professional email assistant. For this email:\n"
    "1) Provide a brief summary\n" 
    "2) Identify action items\n"
    "3) Suggest a professional reply\n"
    f"Email content:\n{email_text}"
)
```

### Additional Providers

Add new email providers by creating a new provider class in `src/email_system/providers/`.

## 📞 Support

If you encounter issues:

1. Check the logs: `journalctl -u pa-email-check.service -f`
2. Test manually: `python3 -m src.main check-emails`
3. Verify authentication: `python3 -m src.main setup-auth`
4. Check environment variables are set correctly

## 🎉 You're All Set!

Your PA_V2 email monitoring system is now running! You'll receive Telegram notifications whenever new emails arrive in Gmail or Outlook, complete with AI-generated summaries and draft replies.
