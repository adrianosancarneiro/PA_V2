#!/bin/bash
# setup_dependencies.sh - Install dependencies for PA_V2 email monitoring

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐍 PA_V2 Email Monitor Dependencies Setup${NC}"
echo "================================================"

UV_CMD=""

# Prefer using `uv` to manage the project's .venv and keep pyproject.toml in sync.
if command -v uv >/dev/null 2>&1; then
    UV_CMD="uv"
    echo -e "${GREEN}✅ Found 'uv' on PATH, will use it to install into .venv${NC}"
else
    echo -e "${YELLOW}⚠ 'uv' not found. Will bootstrap it into .venv and use it.${NC}"
fi

# Create .venv if missing
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment .venv...${NC}"
    python3 -m venv .venv
fi

# Activate venv
echo -e "${YELLOW}📦 Activating .venv...${NC}"
source .venv/bin/activate

if [ -z "$UV_CMD" ]; then
    echo -e "${YELLOW}📥 Installing uv into venv...${NC}"
    # Ensure pip is available in venv
    python -m ensurepip --upgrade || true
    python -m pip install --upgrade pip setuptools wheel
    python -m pip install uv
    UV_CMD=".venv/bin/uv"
fi

echo -e "\n${YELLOW}📦 Installing dependencies into .venv using uv...${NC}"
# Use uv to install the dependencies listed in pyproject.toml (tool.uv.deps)
# Note: some uv versions don't accept --yes
if ${UV_CMD} sync 2>/dev/null; then
    true
else
    echo -e "${YELLOW}⚠ uv sync failed or unsupported; trying uv sync --yes...${NC}"
    if ${UV_CMD} sync --yes 2>/dev/null; then
        true
    else
        echo -e "${RED}❌ uv sync failed, falling back to pip install${NC}"
        python -m pip install requests
        python -m pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
        python -m pip install msal
        python -m pip install python-telegram-bot
        python -m pip install python-dateutil
    fi
fi

echo -e "\n${GREEN}✅ All dependencies installed into .venv!${NC}"

echo -e "\n${BLUE}🧪 Testing imports...${NC}"
python3 -c "
import sys
sys.path.insert(0, 'src')
print('Testing email system...')
from email_system.integration import get_latest_emails, EmailProviderRegistry
print('✅ Email integration working')

print('Testing providers...')
try:
    from email_system.providers.gmail_provider import GmailProvider
    print('✅ Gmail provider available')
except ImportError as e:
    print(f'❌ Gmail provider failed: {e}')

try:
    from email_system.providers.outlook_provider import OutlookGraphProvider
    print('✅ Outlook provider available')
except ImportError as e:
    print(f'❌ Outlook provider failed: {e}')

print('Testing email checker...')
from jobs.email_check import check_auth_status
print('✅ Email checker working')
print('Auth status:', check_auth_status())
"

echo -e "\n${GREEN}🎉 Setup complete!${NC}"
echo -e "\n${BLUE}📝 Next steps:${NC}"
echo "1. Setup email authentication: python3 -m src.main setup-auth"
echo "2. Test email checking: python3 -m src.main check-emails"
echo "3. Set Telegram environment variables:"
echo "   export TELEGRAM_BOT_TOKEN='your_token'"
echo "   export TELEGRAM_CHAT_ID='your_chat_id'"
echo "4. Install the service: ./install_email_monitor.sh"

echo -e "\n${YELLOW}💡 Available commands:${NC}"
echo "• python3 -m src.main list-providers"
echo "• python3 -m src.main check-emails"
echo "• python3 -m src.main monitor-emails"
