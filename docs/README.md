# PA_V2 - Personal│       ├── 📁 email_system/    # Email integration modules
│       │   ├── 📄 __init__.py
│       │   ├── 📄 integration.py    # Main email integration logic
│       │   └── 📁 providers/        # Email provider implementationsistant Version 2

A modular email integration system with support for multiple email providers and bot interfaces.

## 📁 Project Structure

```
PA_V2/
├── 📄 main.py              # Legacy entry point (use pa-v2 command instead)
├── 📄 pyproject.toml       # Project configuration and dependencies  
├── 📄 uv.lock             # UV dependency lock file
├── 📄 .env                # Environment variables (create if needed)
├── 📄 .gitignore          # Git ignore rules
│
├── 📁 src/                # Main source code (Python package)
│   └── 📁 pa_v2/          # Main package directory
│       ├── 📄 __init__.py      # Package initialization
│       ├── � main.py          # CLI entry point module
│       ├── �📁 email/           # Email integration modules
│       │   ├── 📄 __init__.py
│       │   ├── 📄 integration.py    # Main email integration logic
│       │   └── 📁 providers/        # Email provider implementations
│       │       ├── 📄 __init__.py
│       │       ├── 📄 gmail_provider.py
│       │       ├── 📄 outlook_provider.py
│       │       └── 📄 dummy_provider.py
│       │
│       └── 📁 bots/          # Bot implementations
│           ├── 📄 __init__.py
│           └── 📄 telegram_bot_email.py
│
├── 📁 config/            # Configuration files
│   ├── 📄 client_secret_*.json  # OAuth client secrets
│   ├── 📄 gmail_token.json      # Gmail authentication tokens
│   └── 📄 token.json            # Generic token storage
│
├── 📁 tools/             # Utility and setup scripts
│   ├── 📄 setup_email_auth.py   # Email authentication setup
│   └── 📄 quickstart.py         # Quick setup script
│
├── 📁 scripts/           # Shell scripts and automation
│   └── 📄 run_email_test.sh     # Test runner script
│
├── 📁 tests/             # Test files
│   ├── 📄 test_email_integration.py
│   ├── 📄 test_outlook_provider.py
│   ├── 📄 byu_email_test.py
│   └── 📄 byu_email_test_graph.py
│
├── 📁 docs/              # Documentation
│   ├── 📄 README_EMAIL_AUTH.md
│   └── 📄 README_EMAIL_INTEGRATION.md
│
└── 📁 n8n/              # n8n workflow automation files
    └── ...
```

## 🚀 Quick Start

### 1. Setup Environment with UV

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies using UV (recommended)
uv sync

# Or install in development mode
uv pip install -e .
```

### 2. Setup Email Authentication

```bash
# Using the CLI command (recommended)
pa-v2 setup-auth

# Or using Python module
python -m pa_v2.main setup-auth

# Or run the setup tool directly
python tools/setup_email_auth.py
```

### 3. Test Email Integration

```bash
# Using CLI (recommended)
pa-v2 test

# Or using Python module
python -m pa_v2.main test

# Or run tests directly
python tests/test_email_integration.py
```

### 4. Send an Email

```bash
# Using CLI (recommended)
pa-v2 send-email --provider gmail --to user@example.com --subject "Test" --body "Hello!"

# Or using Python module
python -m pa_v2.main send-email --provider gmail --to user@example.com --subject "Test" --body "Hello!"
```

## 📚 Usage Examples

### Python API

```python
import pa_v2

# Send email using the package
result = pa_v2.send_email("gmail", "user@example.com", "Subject", "Body")

# Get latest emails  
emails = pa_v2.get_latest_emails("gmail", count=5)

# List available providers
providers = pa_v2.EmailProviderRegistry.get_all_providers()
```

### Direct Module Import

```python
from pa_v2.email_system.integration import send_email, get_latest_emails

# Send email
result = send_email("gmail", "user@example.com", "Subject", "Body")

# Get latest emails  
emails = get_latest_emails("gmail", count=5)
```

### Bot Integration

```python
from pa_v2.bots.telegram_bot_email import bot_send_email, bot_get_emails

# Bot-friendly functions that handle authentication gracefully
emails = bot_get_emails("gmail", count=10)
result = bot_send_email("gmail", "user@example.com", "Subject", "Body")
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with your configuration:

```env
# Optional: Override default paths
CONFIG_DIR=./config

# For BYU Outlook integration
BYU_CLIENT_ID=your_byu_client_id
BYU_TENANT=byu.edu
BYU_USER=your_email@byu.edu
```

### OAuth Setup

1. Place your Google OAuth client secret in `config/client_secret_*.json`
2. Run `pa-v2 setup-auth` to complete OAuth flow
3. Tokens will be stored in the `config/` directory

## 🧪 Testing

Run all tests using UV:
```bash
# Using the provided script (handles UV setup)
./scripts/run_email_test.sh

# Or manually with proper environment
source .venv/bin/activate
uv sync
python tests/test_email_integration.py
python tests/test_outlook_provider.py
```

## 📋 Available Commands

```bash
# List all available commands
pa-v2 --help

# Available commands:
pa-v2 setup-auth         # Setup email authentication
pa-v2 test              # Run email integration tests  
pa-v2 list-providers    # List available email providers
pa-v2 send-email        # Send an email via command line
```

## 🔌 Adding New Email Providers

1. Create a new provider in `src/pa_v2/email_system/providers/`
2. Implement the `EmailProviderInterface`
3. The provider will be auto-discovered and registered

Example:
```python
# src/pa_v2/email_system/providers/my_provider.py
class MyEmailProvider:
    @staticmethod
    def get_name() -> str:
        return "my_provider"
    
    @staticmethod 
    def send_email(to_addr: str, subject: str, body: str, html_body=None, **kwargs):
        # Implementation here
        return {"success": True, "message": "Email sent"}
```

## 📦 UV Package Management

This project uses [UV](https://docs.astral.sh/uv/) for fast Python package management:

```bash
# Add new dependencies
uv add package_name

# Add development dependencies
uv add --dev pytest

# Remove dependencies
uv remove package_name

# Update all dependencies
uv sync --upgrade

# Install from lock file
uv sync
```

## 📝 Migration Notes

### Import Path Changes:
- **Old**: `from email_integration import send_email`
- **New**: `from pa_v2.email_system.integration import send_email`
- **Or**: `import pa_v2; pa_v2.send_email(...)`

### File Locations:
- Configuration files moved from root to `config/`
- Test files moved to `tests/`
- Tools moved to `tools/`
- Source code now in `src/pa_v2/`

### Command Changes:
- **Old**: `python email_integration.py`
- **New**: `pa-v2 <command>` or `python -m pa_v2.main <command>`

## 🗂️ Old vs New Structure Comparison

| Old Location | New Location |
|-------------|-------------|
| `email_integration.py` | `src/pa_v2/email_system/integration.py` |
| `email_plugins/` | `src/pa_v2/email_system/providers/` |
| `telegram_bot_email.py` | `src/pa_v2/bots/telegram_bot_email.py` |
| `*.json` (configs) | `config/*.json` |
| `test_*.py` | `tests/test_*.py` |
| `setup_email_auth.py` | `tools/setup_email_auth.py` |

## 🛠️ Development

### Installing in Development Mode

```bash
# Install package in editable mode with UV
uv pip install -e .

# This allows you to modify source code and see changes immediately
```

### Running Tests

```bash
# Run all tests
uv run python -m pytest tests/

# Run specific test
uv run python tests/test_email_integration.py
```
