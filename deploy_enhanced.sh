#!/bin/bash
set -euo pipefail

echo "🚀 Deploying PA_V2 Enhanced Services (Timer + Webhooks)..."

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

echo "📋 Deployment Summary:"
echo "   🔄 Timer services: pa-email-check (every 2min)"
echo "   📡 Webhook API: pa-webhook-api (port 8080)"
echo "   🔔 Gmail watch: pa-gmail-watch (every 6h)"
echo "   🤖 Telegram bot: pa-telegram-bot"
echo

# Install systemd services
echo "📦 Installing systemd services..."
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
systemctl is-active pa-email-check.timer && echo -e "   ✅ Email check timer: ${GREEN}active${NC}" || echo -e "   ❌ Email check timer: ${RED}inactive${NC}"
systemctl is-active pa-telegram-bot.service && echo -e "   ✅ Telegram bot: ${GREEN}active${NC}" || echo -e "   ❌ Telegram bot: ${RED}inactive${NC}"
systemctl is-active pa-webhook-api.service && echo -e "   ✅ Webhook API: ${GREEN}active${NC}" || echo -e "   ❌ Webhook API: ${RED}inactive${NC}"
systemctl is-active pa-gmail-watch.timer && echo -e "   ✅ Gmail watch: ${GREEN}active${NC}" || echo -e "   ❌ Gmail watch: ${RED}inactive${NC}"

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
echo -e "${GREEN}✅ Enhanced PA_V2 services deployed successfully!${NC}"
