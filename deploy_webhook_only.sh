#!/bin/bash
set -euo pipefail

echo "🚀 Deploying PA_V2 Webhook-Only Services (No Timer Duplication)..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}❌ This script should not be run as root${NC}"
   exit 1
fi

echo "📋 Webhook-Only Deployment Summary:"
echo "   📡 Webhook API: pa-webhook-api (port 8080) - Real-time Gmail push"
echo "   🔔 Gmail watch: pa-gmail-watch (every 6h) - Renew push subscriptions"
echo "   🤖 Telegram bot: pa-telegram-bot - Interactive email management"
echo "   ❌ Timer polling: DISABLED - Prevents email duplication"
echo

# Stop and disable timer services to prevent duplication
echo "🛑 Stopping timer services to prevent email duplication..."
sudo systemctl stop pa-email-check.timer 2>/dev/null || true
sudo systemctl disable pa-email-check.timer 2>/dev/null || true
sudo systemctl stop pa-email-check.service 2>/dev/null || true
sudo systemctl disable pa-email-check.service 2>/dev/null || true

# Install webhook services  
echo "📦 Installing webhook services..."
sudo cp systemd/pa-webhook-api.service /etc/systemd/system/
sudo cp systemd/pa-gmail-watch.service /etc/systemd/system/
sudo cp systemd/pa-gmail-watch.timer /etc/systemd/system/

# Reload systemd
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

# Enable and start webhook API
echo "🌐 Starting webhook API service..."
sudo systemctl enable pa-webhook-api.service
sudo systemctl start pa-webhook-api.service

# Enable and start Gmail watch
echo "📧 Starting Gmail watch service..."
sudo systemctl enable pa-gmail-watch.timer
sudo systemctl start pa-gmail-watch.timer

# Show status
echo
echo "📊 Service Status:"
systemctl is-active pa-telegram-bot.service && echo -e "   ✅ Telegram bot: ${GREEN}active${NC}" || echo -e "   ❌ Telegram bot: ${RED}inactive${NC}"
systemctl is-active pa-webhook-api.service && echo -e "   ✅ Webhook API: ${GREEN}active${NC}" || echo -e "   ❌ Webhook API: ${RED}inactive${NC}"
systemctl is-active pa-gmail-watch.timer && echo -e "   ✅ Gmail watch: ${GREEN}active${NC}" || echo -e "   ❌ Gmail watch: ${RED}inactive${NC}"

# Confirm timer is disabled
if systemctl is-active pa-email-check.timer >/dev/null 2>&1; then
    echo -e "   ⚠️  Email timer: ${YELLOW}still running (manual stop needed)${NC}"
else
    echo -e "   ✅ Email timer: ${GREEN}disabled (no duplication)${NC}"
fi

echo
echo "🔍 Service URLs:"
echo "   📡 Webhook API: http://localhost:8080"
echo "   📡 Health check: http://localhost:8080/"
echo "   📧 Gmail webhook: http://localhost:8080/hooks/gmail"

echo
echo "⚠️  IMPORTANT: Next Steps Required:"
echo "   1. 🔧 Update /etc/pa_v2/secrets.env with webhook variables"
echo "   2. ☁️  Set up Google Cloud Pub/Sub topic and subscription" 
echo "   3. 🌐 Configure public URL/domain for webhook endpoint"
echo "   4. 🔐 Set up Gmail API push notifications in Google Console"
echo "   5. 🧪 Test webhook with: curl http://localhost:8080/"

echo
echo "📧 Email Flow Summary:"
echo "   📨 BYU emails → BYU Outlook (original) + Gmail copy (BYU_ASC59)"
echo "   📡 Webhook catches Gmail copies in real-time"
echo "   🚫 No timer = No duplication from BYU originals"
echo "   ✅ Result: Clean, real-time email processing"

echo
echo -e "${GREEN}✅ Webhook-only PA_V2 services deployed successfully!${NC}"
