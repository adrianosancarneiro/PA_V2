import base64, ssl, imaplib, smtplib
import msal

TENANT   = "byu.edu"      # BYU tenant domain (try this instead of GUID)
CLIENTID = "9e5f94bc-e8a4-4e73-b8be-63364c29d753"                  # ask OIT for this
USER     = "asc59@byu.edu"
SCOPES   = [
    "https://outlook.office365.com/IMAP.AccessAsUser.All",
    "https://outlook.office365.com/SMTP.Send"
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

def xoauth2(user, token):
    s = f"user={user}\x01auth=Bearer {token}\x01\x01"
    encoded = base64.b64encode(s.encode()).decode()
    print(f"XOAUTH2 string preview: {s[:50]}...")
    return encoded

token = acquire_token()
auth = xoauth2(USER, token)
ctx = ssl.create_default_context()

print(f"\nAttempting to connect to IMAP as user: {USER}")
print(f"Auth string length: {len(auth)} characters")

# IMAP
try:
    imap = imaplib.IMAP4_SSL("outlook.office365.com", 993, ssl_context=ctx)
    print("✓ IMAP connection established")
    
    # Try alternative XOAUTH2 format
    auth_cmd = f"AUTHENTICATE XOAUTH2 {auth}"
    print(f"Auth command preview: {auth_cmd[:50]}...")
    
    # Method 1: Standard authenticate
    try:
        imap.authenticate("XOAUTH2", lambda _: auth)
        print("✓ IMAP authentication successful (method 1)")
    except Exception as e1:
        print(f"✗ IMAP method 1 failed: {e1}")
        
        # Method 2: Direct command - but need to handle the response properly
        try:
            # Send the AUTHENTICATE command properly
            typ, dat = imap._simple_command("AUTHENTICATE", "XOAUTH2")
            if typ == 'OK':
                # Send the auth string
                typ2, dat2 = imap._simple_command(auth)
                if typ2 == 'OK':
                    print(f"✓ IMAP authentication successful (method 2): {typ2}, {dat2}")
                else:
                    raise Exception(f"Auth string failed: {typ2}, {dat2}")
            else:
                raise Exception(f"AUTHENTICATE command failed: {typ}, {dat}")
        except Exception as e2:
            print(f"✗ IMAP method 2 failed: {e2}")
            
            # Method 3: Try the raw approach
            try:
                # Close and reconnect
                imap.logout()
                imap = imaplib.IMAP4_SSL("outlook.office365.com", 993, ssl_context=ctx)
                
                # Manual AUTHENTICATE
                imap.send(b'A001 AUTHENTICATE XOAUTH2\r\n')
                response = imap.readline()
                print(f"Server response to AUTHENTICATE: {response}")
                
                if b'+' in response:  # Server is ready for auth string
                    imap.send(auth.encode() + b'\r\n')
                    final_response = imap.readline()
                    print(f"Final auth response: {final_response}")
                    
                    if b'OK' in final_response:
                        print("✓ IMAP authentication successful (method 3)")
                    else:
                        raise Exception(f"Auth failed: {final_response}")
                else:
                    raise Exception(f"Unexpected server response: {response}")
                    
            except Exception as e3:
                print(f"✗ IMAP method 3 failed: {e3}")
                raise e1  # Re-raise the original exception
    
    # Check IMAP state
    print(f"IMAP state: {imap.state}")
    
    if imap.state == 'AUTH':
        imap.select("INBOX")
        result = imap.search(None, "ALL")
        print(f"✓ INBOX search result: {result}")
        imap.logout()
        print("✓ IMAP logout successful")
    else:
        print(f"✗ IMAP not in AUTH state: {imap.state}")
    
except Exception as e:
    print(f"✗ IMAP error: {e}")
    print(f"Error type: {type(e).__name__}")

# SMTP
try:
    print(f"\nAttempting to connect to SMTP as user: {USER}")
    smtp = smtplib.SMTP("smtp.office365.com", 587)
    print("✓ SMTP connection established")
    
    smtp.starttls(context=ctx)
    print("✓ SMTP STARTTLS successful")
    
    smtp.docmd("AUTH", "XOAUTH2 " + auth)
    print("✓ SMTP authentication successful")
    
    smtp.sendmail(USER, [USER], "Subject: XOAUTH2 test\r\n\r\nHello from Python OAuth2.")
    print("✓ Email sent successfully")
    
    smtp.quit()
    print("✓ SMTP quit successful")
    
except Exception as e:
    print(f"✗ SMTP error: {e}")
    print(f"Error type: {type(e).__name__}")
