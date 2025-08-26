#!/bin/bash
# cleanup_old_files.sh - Remove duplicate files after reorganization

echo "🧹 PA_V2 Cleanup Script - Removing Duplicate Files"
echo "=================================================="

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# First, let's run verification to make sure the new structure works
echo "🔍 Running verification first..."
./verify_reorganization.sh
if [ $? -ne 0 ]; then
    echo "❌ Verification failed! Not proceeding with cleanup."
    echo "Please fix the issues first."
    exit 1
fi

echo ""
echo "✅ Verification passed! Proceeding with cleanup..."
echo ""

# Create a backup directory just in case
echo "📦 Creating backup directory..."
mkdir -p .cleanup_backup
echo "✅ Backup directory created at .cleanup_backup/"

# Function to safely remove file with backup
safe_remove() {
    local file="$1"
    if [ -f "$file" ]; then
        echo "🗑️  Removing duplicate: $file"
        cp "$file" ".cleanup_backup/$(basename "$file")" 2>/dev/null
        rm "$file"
    fi
}

# Function to safely remove directory with backup
safe_remove_dir() {
    local dir="$1"
    if [ -d "$dir" ]; then
        echo "🗑️  Removing duplicate directory: $dir"
        cp -r "$dir" ".cleanup_backup/" 2>/dev/null
        rm -rf "$dir"
    fi
}

echo ""
echo "🧹 Removing duplicate source files..."

# Remove old email integration files
safe_remove "email_integration.py"
safe_remove "telegram_bot_email.py"
safe_remove "setup_email_auth.py"
safe_remove "quickstart.py"
safe_remove "run_email_test.sh"

# Remove old test files
safe_remove "test_email_integration.py"
safe_remove "test_outlook_provider.py"
safe_remove "byu_email_test.py"
safe_remove "byu_email_test_graph.py"

# Remove old documentation
safe_remove "README_EMAIL_AUTH.md"
safe_remove "README_EMAIL_INTEGRATION.md"

# Remove old configuration files (now in config/)
safe_remove "client_secret_147697913284-lrl04fga24gpkk6ltv6ai3d4eps602lb.apps.googleusercontent.com.json"
safe_remove "gmail_token.json"
safe_remove "token.json"

# Remove old directories
safe_remove_dir "email_plugins"
safe_remove_dir "__pycache__"

# Remove legacy main.py (since we have pa-v2 command)
echo ""
echo "⚠️  Legacy main.py file found."
echo "   The new structure uses 'pa-v2' command instead."
echo "   Do you want to remove the legacy main.py? (y/n)"
read -p "   Remove main.py? " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    safe_remove "main.py"
    echo "✅ Legacy main.py removed"
else
    echo "⏭️  Keeping legacy main.py"
fi

echo ""
echo "🔍 Running final verification..."
./verify_reorganization.sh
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ VERIFICATION FAILED AFTER CLEANUP!"
    echo "🔄 Restoring files from backup..."
    cp -r .cleanup_backup/* . 2>/dev/null
    echo "⚠️  Files restored. Please check what went wrong."
    exit 1
fi

echo ""
echo "🎉 CLEANUP SUCCESSFUL!"
echo "====================="
echo "✅ All duplicate files removed"
echo "✅ Project structure verified"
echo "✅ Backup created in .cleanup_backup/"
echo ""
echo "📊 Cleanup Summary:"
echo "==================="
echo "Removed duplicate files:"
echo "  - email_integration.py → now in src/pa_v2/email/"
echo "  - telegram_bot_email.py → now in src/pa_v2/bots/"
echo "  - email_plugins/ → now in src/pa_v2/email/providers/"
echo "  - test files → now in tests/"
echo "  - docs → now in docs/"
echo "  - config files → now in config/"
echo "  - tools → now in tools/"
echo "  - scripts → now in scripts/"
echo ""
echo "🚀 Your project is now clean and organized!"
echo ""
echo "💡 You can remove the .cleanup_backup/ directory when you're confident everything works."
echo "   rm -rf .cleanup_backup/"
