#!/bin/bash
set -euo pipefail

echo "🚀 Deploying PA_V2 Hybrid Services (Webhook Reading + BYU Sending)..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "📋 Hybrid Architecture Summary:"
echo "   📡 Gmail Webhook: Real-time reading (INBOX + BYU_ASC59)"
echo "   🔔 Gmail Watch: Renew push subscriptions every 6h"
echo "   🎯 BYU Provider: Kept for sending/replying (maintain identity)"
echo "   🤖 Telegram Bot: Enhanced with proper reply routing"
echo "   ❌ Timer Polling: DISABLED (prevents duplication)"
echo

echo "🔧 Key Features:"
echo "   ✅ Read: Gmail webhook captures forwarded emails instantly"
echo "   ✅ Reply: BYU Outlook maintains professional identity"
echo "   ✅ Threading: Proper conversation continuity"
echo "   ✅ Contacts: Access full BYU directory for compose"
echo "   ✅ No Duplication: Only Gmail copies stored"

# Install webhook services (same as webhook-only)
echo "📦 Installing webhook services..."
sudo cp systemd/pa-webhook-api.service /etc/systemd/system/
sudo cp systemd/pa-gmail-watch.service /etc/systemd/system/
sudo cp systemd/pa-gmail-watch.timer /etc/systemd/system/

# Stop timer to prevent duplication, but keep BYU provider available
echo "🛑 Stopping timer polling (prevents duplication)..."
sudo systemctl stop pa-email-check.timer 2>/dev/null || true
sudo systemctl disable pa-email-check.timer 2>/dev/null || true

# Reload systemd
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

# Enable and start services
echo "🌐 Starting hybrid services..."
sudo systemctl enable pa-webhook-api.service
sudo systemctl start pa-webhook-api.service
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
echo "📧 Email Flow Architecture:"
echo "   ┌─ READING ────────────────────────────────────┐"
echo "   │ BYU Email → BYU Outlook → Gmail (BYU_ASC59)  │"
echo "   │ Gmail Webhook → Database (Gmail metadata)    │"
echo "   └──────────────────────────────────────────────┘"
echo "   ┌─ REPLYING ───────────────────────────────────┐"  
echo "   │ User clicks Reply → Detect BYU_ASC59 tag     │"
echo "   │ Route to BYU Provider → Send from asc59@byu  │"
echo "   └──────────────────────────────────────────────┘"

echo
echo "⚠️  IMPORTANT: Next Steps Required:"
echo "   1. 🔧 Update compose handlers to route BYU emails via Outlook"
echo "   2. 🏷️ Enhance reply detection for BYU_ASC59 tagged emails"
echo "   3. ☁️  Set up Google Cloud Pub/Sub + Gmail push notifications"
echo "   4. 🧪 Test hybrid workflow: Gmail reading + BYU replying"

echo
echo -e "${GREEN}✅ Hybrid PA_V2 architecture deployed successfully!${NC}"
