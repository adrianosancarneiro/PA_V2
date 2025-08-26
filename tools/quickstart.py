import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']

def main():
    creds = None
    # Look for token in config directory
    config_dir = os.path.join(os.path.dirname(__file__), "..", "config")
    token_path = os.path.join(config_dir, 'token.json')
    credentials_path = os.path.join(config_dir, 'client_secret_147697913284-lrl04fga24gpkk6ltv6ai3d4eps602lb.apps.googleusercontent.com.json')
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    service = build('gmail', 'v1', credentials=creds)
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    print('Labels:')
    for label in labels:
        print(label['name'])

if __name__ == '__main__':
    main()
