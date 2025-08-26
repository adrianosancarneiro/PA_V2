import requests
import msal

TENANT   = "byu.edu"      # BYU tenant domain
CLIENTID = "9e5f94bc-e8a4-4e73-b8be-63364c29d753"                  # ask OIT for this
USER     = "asc59@byu.edu"
SCOPES   = [
    "https://graph.microsoft.com/Mail.ReadWrite",
    "https://graph.microsoft.com/Mail.Send"
]

def acquire_token():
    app = msal.PublicClientApplication(CLIENTID, authority=f"https://login.microsoftonline.com/{TENANT}")
    flow = app.initiate_device_flow(scopes=SCOPES)
    print(f"\nOpen {flow['verification_uri']} and enter code: {flow['user_code']}\n")
    result = app.acquire_token_by_device_flow(flow)
    
    print("Token acquisition result:")
    if "access_token" in result:
        print("✓ Access token acquired successfully")
        print(f"Token expires in: {result.get('expires_in', 'unknown')} seconds")
        if "scope" in result:
            print(f"Granted scopes: {result['scope']}")
    else:
        print("✗ Failed to acquire access token")
        print(f"Error: {result}")
        raise RuntimeError(result)
    
    return result["access_token"]

def test_graph_api(token):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Test reading emails
    print("\nTesting Microsoft Graph API...")
    try:
        # Get user's messages
        url = "https://graph.microsoft.com/v1.0/me/messages?$top=5&$select=subject,from,receivedDateTime"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            messages = response.json()
            print(f"✓ Successfully retrieved {len(messages.get('value', []))} messages")
            for msg in messages.get('value', [])[:3]:  # Show first 3
                print(f"  - {msg.get('subject', 'No subject')} from {msg.get('from', {}).get('emailAddress', {}).get('address', 'Unknown')}")
        else:
            print(f"✗ Failed to get messages: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"✗ Graph API error: {e}")

    # Test sending email
    try:
        print("\nTesting email sending via Graph API...")
        email_data = {
            "message": {
                "subject": "Graph API Test",
                "body": {
                    "contentType": "Text",
                    "content": "Hello from Python via Microsoft Graph API!"
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": USER
                        }
                    }
                ]
            }
        }
        
        url = "https://graph.microsoft.com/v1.0/me/sendMail"
        response = requests.post(url, headers=headers, json=email_data)
        
        if response.status_code == 202:
            print("✓ Email sent successfully via Graph API")
        else:
            print(f"✗ Failed to send email: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"✗ Email sending error: {e}")

if __name__ == "__main__":
    token = acquire_token()
    test_graph_api(token)
