#!/bin/bash
# verification_script.sh - Test the reorganized project structure

echo "🔍 PA_V2 Reorganization Verification Script"
echo "=========================================="

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Activate virtual environment
echo "📦 Activating virtual environment..."
source "$PROJECT_ROOT/.venv/bin/activate"

# Test UV sync
echo "🔄 Testing UV sync..."
uv sync
if [ $? -ne 0 ]; then
    echo "❌ UV sync failed"
    exit 1
else
    echo "✅ UV sync successful"
fi

# Test package import
echo "📥 Testing package import..."
python -c "import pa_v2; print('✅ Package import successful')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Package import failed"
    exit 1
fi

# Test CLI entry point
echo "🎯 Testing CLI entry point..."
pa-v2 --help > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ CLI entry point failed"
    exit 1
else
    echo "✅ CLI entry point working"
fi

# Test list providers
echo "📋 Testing provider listing..."
OUTPUT=$(pa-v2 list-providers 2>/dev/null)
if echo "$OUTPUT" | grep -q "gmail"; then
    echo "✅ Gmail provider loaded"
else
    echo "❌ Gmail provider not found"
    exit 1
fi

# Test Python module execution
echo "🐍 Testing Python module execution..."
python -m pa_v2.main list-providers > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Python module execution failed"
    exit 1
else
    echo "✅ Python module execution working"
fi

# Test config directory
echo "📁 Testing config directory..."
if [ -f "$PROJECT_ROOT/config/client_secret_147697913284-lrl04fga24gpkk6ltv6ai3d4eps602lb.apps.googleusercontent.com.json" ]; then
    echo "✅ Config files found in config directory"
else
    echo "⚠️  Config files not found in config directory"
fi

# Test src structure
echo "🏗️  Testing source structure..."
if [ -d "$PROJECT_ROOT/src/pa_v2" ]; then
    echo "✅ Source structure correct"
else
    echo "❌ Source structure incorrect"
    exit 1
fi

# Test imports within package
echo "🔗 Testing internal imports..."
python -c "
import sys
sys.path.insert(0, 'src')
from pa_v2.email.integration import EmailProviderRegistry
from pa_v2.bots.telegram_bot_email import check_email_auth_status
print('✅ Internal imports working')
" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Internal imports failed"
    exit 1
fi

echo ""
echo "🎉 ALL TESTS PASSED!"
echo "=========================================="
echo "✅ Project reorganization successful"
echo "✅ UV integration working"
echo "✅ Package structure correct"
echo "✅ CLI commands functional"
echo "✅ Imports working correctly"
echo ""
echo "🚀 Your PA_V2 project is ready to use!"
echo ""
echo "Quick commands to try:"
echo "  pa-v2 list-providers"
echo "  pa-v2 setup-auth"
echo "  pa-v2 --help"
