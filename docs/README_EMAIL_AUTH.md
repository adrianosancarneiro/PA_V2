# Email Authentication Setup Guide

This guide covers the setup process for both Gmail and Microsoft Outlook (BYU) email providers in the PA_V2 system.

## Overview

The PA_V2 email monitoring system supports two email providers:
- **Gmail**: Uses Google API with OAuth2 authentication
- **Microsoft Outlook (BYU)**: Uses Microsoft Graph API with Azure AD authentication

Both providers store authentication tokens in the `config/` directory for automatic token refresh.

## Quick Setup

Run the authentication setup script to configure both providers:

```bash
python tools/setup_email_auth.py
```

This interactive script will guide you through setting up authentication for both Gmail and Outlook providers.

## Authentication File Locations

All authentication tokens are stored in the `config/` directory:

- **Gmail**: `config/gmail_token.json`
- **Outlook (BYU)**: `config/byu_outlook_token_cache.json`
- **Google Client Secrets**: `config/client_secret_*.json`

## Gmail Setup

### Prerequisites

1. **Install Required Packages** (handled by `setup_dependencies.sh`):
   ```bash
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
   ```

2. **Google Cloud Console Setup**:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Gmail API
   - Create OAuth 2.0 credentials for a desktop application
   - Download the client secret JSON file
   - Place it in the `config/` directory

### Authentication Process

The Gmail provider uses OAuth2 with the following scopes:
- `https://www.googleapis.com/auth/gmail.readonly` (read emails)
- `https://www.googleapis.com/auth/gmail.send` (send emails)

On first run, it will:
1. Open a web browser for Google OAuth consent
2. Save the refresh token to `config/gmail_token.json`
3. Automatically refresh tokens as needed

## Microsoft Outlook (BYU) Setup

### Prerequisites

1. **Install Required Packages** (handled by `setup_dependencies.sh`):
   ```bash
   pip install msal
   ```

2. **Environment Variables**:
   The system expects these variables in `/etc/pa_v2/secrets.env`:
   ```bash
   BYU_CLIENT_ID=9e5f94bc-e8a4-4e73-b8be-63364c29d753
   BYU_TENANT=byu.edu
   BYU_USER=your_netid@byu.edu
   ```

### Authentication Process

The Outlook provider uses Microsoft Graph API with device code flow:

1. Run the setup script: `python tools/setup_email_auth.py`
2. Select option 2 for BYU Outlook authentication
3. Visit the provided Microsoft device login URL
4. Enter the device code shown in the terminal
5. Complete BYU authentication in your browser
6. The token will be saved to `config/byu_outlook_token_cache.json`

### Required Permissions

The Outlook provider requires these Microsoft Graph API scopes:
- `https://graph.microsoft.com/Mail.Read` (read emails)
- `https://graph.microsoft.com/Mail.Send` (send emails)

## Troubleshooting

### Gmail Issues

1. **"The file token.json stores the user's access and refresh tokens"**
   - This is normal - the token file will be created on first authentication

2. **"Please visit this URL to authorize this application"**
   - Open the provided URL in your browser and complete the OAuth flow

3. **"Credentials have been saved"**
   - Authentication successful - tokens are cached for future use

### Outlook Issues

1. **"No valid cached token available and interactive mode disabled"**
   - Run `python tools/setup_email_auth.py` to complete initial authentication

2. **"BYU_CLIENT_ID not found in environment variables"**
   - Ensure `/etc/pa_v2/secrets.env` contains the BYU_CLIENT_ID

3. **"Authentication failed"**
   - Verify your BYU credentials and network connection
   - Ensure the client ID has proper permissions

### Token Refresh

Both providers automatically refresh tokens:
- **Gmail**: Uses refresh_token in `gmail_token.json`
- **Outlook**: Uses cached tokens in `byu_outlook_token_cache.json`

If tokens expire or become invalid, re-run the setup script.

## Security Notes

1. **Token Files**: Keep `config/*.json` files secure - they contain access credentials
2. **Secrets File**: `/etc/pa_v2/secrets.env` should have restricted permissions (600)
3. **Environment Variables**: Never commit credentials to version control

## Integration with Email Check Job

Once authentication is complete, the email check job (`src/jobs/email_check.py`) will:

1. Load authentication tokens automatically
2. Check authentication status on startup
3. Skip providers that aren't authenticated
4. Log authentication status for troubleshooting

Example output:
```
Authentication Status:
  gmail: ✅ Ready
  outlook: ✅ Ready
```

## Manual Testing

To test authentication manually:

```bash
# Test Gmail
python -c "from src.email_system.providers.gmail_provider import GmailProvider; print('Gmail auth:', GmailProvider().is_authenticated())"

# Test Outlook
python -c "from src.email_system.providers.outlook_provider import OutlookGraphProvider; print('Outlook auth:', OutlookGraphProvider().is_authenticated())"
```
   ```

4. **Run the Script**:
   ```bash
   python send_outlook_smtp.py
   ```
   or
   ```bash
   python email_integration.py
   ```

## How It Works

1. The script uses Device Code flow, which is perfect for CLI applications.
2. You'll be prompted to visit a Microsoft URL and enter a code.
3. This opens Microsoft's login page where you can sign in with your university credentials.
4. Any MFA/2FA prompt will appear naturally in the browser.
5. After successful authentication, the script gets a token and can send emails on your behalf.

## Benefits

- Works with university accounts that require MFA/2FA
- No need for admin access to Microsoft Entra ID
- More secure than password-based authentication
- Follows Microsoft's recommended authentication practice
- Tokens are cached for reuse, minimizing login prompts
