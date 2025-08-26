# Microsoft Graph API Email Integration

This integration allows you to send emails using Microsoft Graph API with OAuth authentication, which works well with university accounts that have MFA/2FA enabled.

## Setup Instructions

1. **Install Required Packages**:
   ```bash
   uv pip install msal requests google-api-python-client google-auth-httplib2 google-auth-oauthlib
   ```

2. **Register an Application in Microsoft Azure**:

   a. Go to the [Azure App Registration Portal](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
   
   b. Click "New registration"
   
   c. Enter a name for your application (e.g., "PA V2 Email Assistant")
   
   d. Set "Supported account types" to "Accounts in any organizational directory"
   
   e. For "Redirect URI", select "Public client/native (mobile & desktop)" and enter "https://login.microsoftonline.com/common/oauth2/nativeclient"
   
   f. Click "Register"
   
   g. On the Overview page, copy the "Application (client) ID" - you'll need this for the MS_CLIENT_ID environment variable

3. **Set Environment Variables**:
   ```bash
   export MS_CLIENT_ID="your-client-id-from-azure"
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
