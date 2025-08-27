#!/bin/bash
# install_email_monitor.sh - Install PA_V2 email monitoring system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 PA_V2 Email Monitor Installation Script${NC}"
echo "================================================"

# Check if running as root (we shouldn't be)
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ Please do not run this script as root${NC}"
    echo "This script will use sudo when needed"
    exit 1
fi

# Get project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo -e "${BLUE}📁 Project directory: ${PROJECT_DIR}${NC}"

# Check for required environment variables
echo -e "\n${YELLOW}🔍 Checking environment configuration...${NC}"

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  TELEGRAM_BOT_TOKEN not set${NC}"
    echo "Please set your Telegram bot token:"
    echo "export TELEGRAM_BOT_TOKEN='your_bot_token_here'"
fi

if [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo -e "${YELLOW}⚠️  TELEGRAM_CHAT_ID not set${NC}"
    echo "Please set your Telegram chat ID:"
    echo "export TELEGRAM_CHAT_ID='your_chat_id_here'"
fi

# Check Python and dependencies
echo -e "\n${YELLOW}🐍 Checking Python setup...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 not found${NC}"
    exit 1
fi

python3 -c "import requests" 2>/dev/null || {
    echo -e "${YELLOW}📦 Installing requests...${NC}"
    pip3 install requests
}

# Test email authentication
echo -e "\n${YELLOW}🔐 Testing email authentication...${NC}"
cd "$PROJECT_DIR"
python3 -m src.main check-emails 2>/dev/null || {
    echo -e "${YELLOW}⚠️  Email authentication may need setup${NC}"
    echo "Run: python3 -m src.main setup-auth"
}

# Create systemd service files with correct paths
echo -e "\n${YELLOW}📝 Creating systemd service files...${NC}"

# Update service file with environment variables
SERVICE_FILE="/tmp/pa-email-check.service"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=PA: one-shot email check (Gmail + Outlook)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$(whoami)
WorkingDirectory=$PROJECT_DIR
Environment=PYTHONUNBUFFERED=1
Environment=LLAMA_BASE_URL=${LLAMA_BASE_URL:-http://192.168.0.83:8080}
Environment=CONFIG_DIR=$PROJECT_DIR/config
EnvironmentFile=/etc/pa_v2/secrets.env
# Use venv python by default
ExecStart=$PROJECT_DIR/.venv/bin/python -m src.jobs.email_check
EOF

# Install service files
echo -e "${YELLOW}🔧 Installing systemd files...${NC}"
sudo cp "$SERVICE_FILE" /etc/systemd/system/
sudo cp "$PROJECT_DIR/systemd/pa-email-check.timer" /etc/systemd/system/

# Reload systemd
echo -e "${YELLOW}🔄 Reloading systemd...${NC}"
sudo systemctl daemon-reload

# Enable and start timer
echo -e "${YELLOW}⏰ Enabling email check timer...${NC}"
sudo systemctl enable pa-email-check.timer
sudo systemctl start pa-email-check.timer

# Check status
echo -e "\n${GREEN}✅ Installation complete!${NC}"
echo -e "\n${BLUE}📊 Service Status:${NC}"
systemctl is-active pa-email-check.timer && echo -e "${GREEN}✅ Timer is active${NC}" || echo -e "${RED}❌ Timer is not active${NC}"

echo -e "\n${BLUE}⏰ Timer Schedule:${NC}"
systemctl list-timers | grep pa-email || echo "Timer not found in list"

echo -e "\n${BLUE}📖 Useful Commands:${NC}"
echo "• Check timer status: systemctl status pa-email-check.timer"
echo "• View logs: journalctl -u pa-email-check.service -f"
echo "• Stop timer: sudo systemctl stop pa-email-check.timer"
echo "• Start timer: sudo systemctl start pa-email-check.timer"
echo "• Test manually: python3 -m src.main check-emails"

echo -e "\n${YELLOW}📝 Next Steps:${NC}"
echo "1. Set your Telegram bot token and chat ID if not already done"
echo "2. Run: python3 -m src.main setup-auth (if needed)"
echo "3. Test: python3 -m src.main check-emails"
echo "4. Watch logs: journalctl -u pa-email-check.service -f"

echo -e "\n${GREEN}🎉 Email monitoring is now running every minute!${NC}"
