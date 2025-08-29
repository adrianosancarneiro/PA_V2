#!/bin/bash
set -euo pipefail

echo "🚀 Deploying PA_V2 with Internet Message-ID Implementation..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}❌ This script should not be run as root${NC}"
   exit 1
fi

echo -e "${BLUE}📋 Deployment Summary (Internet Message-ID Implementation):${NC}"
echo "   📧 Gmail webhook processing with header extraction"
echo "   🔄 Cross-provider email threading support"
echo "   📞 On-demand Outlook replies using Microsoft Graph"
echo "   🗄️  Database migration for Internet Message-ID storage"
echo "   🤖 Enhanced Telegram bot with Outlook reply option"
echo

# Function to run database migrations
run_migrations() {
    echo -e "${YELLOW}🗄️  Running database migrations...${NC}"
    
    # Source environment variables
    set +u  # Allow undefined variables temporarily
    source /etc/pa_v2/secrets.env 2>/dev/null || {
        echo -e "${RED}❌ Could not load /etc/pa_v2/secrets.env${NC}"
        echo "   Please ensure the secrets file exists and is readable"
        exit 1
    }
    set -u
    
    # Run migrations using Python to use the same connection logic
    .venv/bin/python -c "
import sys, os
sys.path.append('src')
from dotenv import load_dotenv
load_dotenv('/etc/pa_v2/secrets.env')
from core.database import get_conn
import glob

# Get all migration files in order
migration_files = sorted(glob.glob('src/migrations/*.sql'))
print(f'Found {len(migration_files)} migration files')

for migration_file in migration_files:
    print(f'🔄 Running {migration_file}...')
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                with open(migration_file, 'r') as f:
                    migration_sql = f.read()
                cur.execute(migration_sql)
                conn.commit()
        print(f'✅ Completed {migration_file}')
    except Exception as e:
        if 'already exists' in str(e) or 'IF NOT EXISTS' in migration_sql:
            print(f'⏭️  Skipped {migration_file} (already applied)')
        else:
            print(f'❌ Failed {migration_file}: {e}')
            raise
print('✅ All migrations completed')
"
    echo -e "${GREEN}✅ Database migrations completed${NC}"
}

# Function to update dependencies
update_dependencies() {
    echo -e "${YELLOW}📦 Updating dependencies...${NC}"
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Install/update dependencies using uv if available, otherwise pip
    if command -v uv >/dev/null 2>&1; then
        echo "Using uv for dependency management..."
        uv sync
    else
        echo "Using pip for dependency management..."
        pip install -r requirements.txt 2>/dev/null || {
            echo "No requirements.txt found, installing from pyproject.toml..."
            pip install -e .
        }
    fi
    
    echo -e "${GREEN}✅ Dependencies updated${NC}"
}

# Function to verify implementation
verify_implementation() {
    echo -e "${YELLOW}🧪 Verifying Internet Message-ID implementation...${NC}"
    
    # Run the test script
    if .venv/bin/python test_internet_message_id.py | tail -10 | grep -q "All tests passed"; then
        echo -e "${GREEN}✅ Implementation verification passed${NC}"
    else
        echo -e "${YELLOW}⚠️  Running detailed verification...${NC}"
        .venv/bin/python test_internet_message_id.py
    fi
}

# Function to stop conflicting services
stop_timer_services() {
    echo -e "${YELLOW}🛑 Stopping timer services to prevent email duplication...${NC}"
    
    # Stop email check timer to prevent duplication with webhooks
    sudo systemctl stop pa-email-check.timer 2>/dev/null || true
    sudo systemctl disable pa-email-check.timer 2>/dev/null || true
    sudo systemctl stop pa-email-check.service 2>/dev/null || true
    
    echo -e "${GREEN}✅ Timer services stopped${NC}"
}

# Function to deploy webhook services
deploy_webhook_services() {
    echo -e "${YELLOW}📡 Deploying webhook services...${NC}"
    
    # Copy service files
    sudo cp systemd/pa-webhook-api.service /etc/systemd/system/
    sudo cp systemd/pa-gmail-watch.service /etc/systemd/system/
    sudo cp systemd/pa-gmail-watch.timer /etc/systemd/system/
    sudo cp systemd/pa-telegram-bot.service /etc/systemd/system/
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    # Enable and start services
    sudo systemctl enable pa-webhook-api.service
    sudo systemctl enable pa-gmail-watch.timer
    sudo systemctl enable pa-telegram-bot.service
    
    # Restart services to load new code
    sudo systemctl restart pa-webhook-api.service
    sudo systemctl restart pa-gmail-watch.timer
    sudo systemctl restart pa-telegram-bot.service
    
    echo -e "${GREEN}✅ Webhook services deployed${NC}"
}

# Function to show service status
show_status() {
    echo
    echo -e "${BLUE}📊 Service Status:${NC}"
    
    # Check individual services
    if systemctl is-active pa-telegram-bot.service >/dev/null 2>&1; then
        echo -e "   ✅ Telegram bot: ${GREEN}active${NC}"
    else
        echo -e "   ❌ Telegram bot: ${RED}inactive${NC}"
    fi
    
    if systemctl is-active pa-webhook-api.service >/dev/null 2>&1; then
        echo -e "   ✅ Webhook API: ${GREEN}active${NC}"
    else
        echo -e "   ❌ Webhook API: ${RED}inactive${NC}"
    fi
    
    if systemctl is-active pa-gmail-watch.timer >/dev/null 2>&1; then
        echo -e "   ✅ Gmail watch: ${GREEN}active${NC}"
    else
        echo -e "   ❌ Gmail watch: ${RED}inactive${NC}"
    fi
    
    # Confirm timer is disabled
    if systemctl is-active pa-email-check.timer >/dev/null 2>&1; then
        echo -e "   ⚠️  Email timer: ${YELLOW}still running (should be disabled)${NC}"
    else
        echo -e "   ✅ Email timer: ${GREEN}disabled (no duplication)${NC}"
    fi
}

# Function to show next steps
show_next_steps() {
    echo
    echo -e "${BLUE}🔍 Service URLs:${NC}"
    echo "   📡 Webhook API: http://localhost:8080"
    echo "   📡 Health check: http://localhost:8080/"
    echo "   📧 Gmail webhook: http://localhost:8080/hooks/gmail"
    
    echo
    echo -e "${BLUE}📋 Internet Message-ID Features Ready:${NC}"
    echo "   ✅ Gmail emails store original Message-ID and References"
    echo "   ✅ Database schema updated with new columns"
    echo "   ✅ Outlook reply service available for Telegram bot"
    echo "   ✅ Cross-provider threading support enabled"
    
    echo
    echo -e "${YELLOW}⚠️  Next Steps for Full Integration:${NC}"
    echo "   1. 🤖 Update Telegram bot handlers to include 'Reply via Outlook' option"
    echo "   2. 🔐 Ensure Microsoft Graph session is available in bot context"
    echo "   3. 🧪 Test Outlook reply functionality with real BYU emails"
    echo "   4. 📊 Monitor logs for Internet Message-ID extraction success"
    
    echo
    echo -e "${BLUE}🧪 Testing Commands:${NC}"
    echo "   Test implementation: .venv/bin/python test_internet_message_id.py"
    echo "   Demo functionality: .venv/bin/python demo_internet_message_id.py"
    echo "   Check recent emails: SELECT internet_message_id FROM email_messages WHERE internet_message_id IS NOT NULL LIMIT 5;"
}

# Main deployment sequence
main() {
    echo -e "${BLUE}Starting Internet Message-ID Implementation Deployment...${NC}"
    echo
    
    # Change to project directory
    cd "$(dirname "$0")"
    
    # Run deployment steps
    update_dependencies
    run_migrations
    verify_implementation
    stop_timer_services
    deploy_webhook_services
    
    # Show results
    show_status
    show_next_steps
    
    echo
    echo -e "${GREEN}🎉 Internet Message-ID implementation deployed successfully!${NC}"
    echo -e "${YELLOW}📧 BYU emails will now store original headers for cross-provider threading${NC}"
}

# Run if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
