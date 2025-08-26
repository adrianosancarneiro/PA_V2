# Email Integration System

This system provides a unified and extensible way to send emails through different providers (Gmail, Outlook, etc.). The architecture is designed to be modular and easy to extend with new email providers.

## Installation

To use the email integration system, you need to install the required dependencies:

```bash
# Using UV (recommended)
uv pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib msal requests

# Or using pip
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib msal requests
```

## Architecture

The system consists of two main components:

1. **Email Integration Module** (`email_integration.py`): The main module that discovers, registers, and manages providers. It provides a unified interface for sending emails.

2. **Provider Plugins** (in the `email_plugins` directory): Each provider is implemented as a plugin module in the `email_plugins` directory.

### Current Provider Plugins

- `gmail_provider.py`: Implements Google Gmail using OAuth2
- `outlook_provider.py`: Implements both Microsoft Graph API and SMTP methods
- `dummy_provider.py`: A sample provider for testing and demonstration

## How to Use

### Basic Usage

```python
from email_integration import send_email

# Send via Gmail
result = send_email(
    provider="gmail", 
    to="recipient@example.com", 
    subject="Test Email", 
    body="Hello from the email integration system!",
    html_body="<p>Hello from the <b>email integration system</b>!</p>"
)

if result["success"]:
    print(f"Success: {result['message']}")
else:
    print(f"Error: {result['message']}")
```

### Command Line Usage

```bash
# Send an email
python email_integration.py --provider gmail --to recipient@example.com --subject "Test Email" --body "Hello!" --html "<p>Hello!</p>"

# List available providers
python email_integration.py --list-providers

# Interactive mode (prompts for details)
python email_integration.py
```

## Available Providers

- **gmail**: Google Gmail using OAuth2
- **outlook_graph**: Microsoft Outlook using Graph API with OAuth2
- **outlook_smtp**: Microsoft Outlook using SMTP authentication
- **outlook**: Try outlook_graph first, fall back to outlook_smtp if it fails
- **dummy**: A sample provider for testing (doesn't actually send emails)
- Any additional providers loaded from the plugins directory

## Adding New Providers

To add a new email provider:

1. Create a new Python file in the `email_plugins` directory (e.g., `custom_provider.py`)
2. Define a class with the following methods:
   - `get_name()`: Returns the provider name (string)
   - `send_email(to_addr, subject, body, html_body=None, **kwargs)`: Sends an email and returns a result dictionary

Example:

```python
class MyCustomProvider:
    @staticmethod
    def get_name():
        return "custom_provider"
    
    @staticmethod
    def send_email(to_addr, subject, body, html_body=None, **kwargs):
        # Your implementation here
        
        return {
            "success": True,
            "message": "Email sent successfully",
            "provider": "custom_provider"
        }
```

The provider will be automatically discovered and registered when the `email_integration.py` module is loaded.

## Configuration

Each provider may have its own configuration requirements:

- **Gmail**: Requires OAuth credentials in a client secrets JSON file
- **Outlook Graph**: Requires a Microsoft client ID (set via MS_CLIENT_ID environment variable)
- **Outlook SMTP**: Requires email and password (set via OUTLOOK_EMAIL and OUTLOOK_PASS environment variables)

See each provider's module for detailed configuration instructions.
