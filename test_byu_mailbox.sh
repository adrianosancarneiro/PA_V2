#!/bin/bash
# Test script to check if BYU Outlook mailbox is empty (due to redirects)

echo "🔍 Testing BYU Outlook Mailbox State..."

cd /home/mentorius/AI_Services/PA_V2

.venv/bin/python -c "
import sys
sys.path.append('src')
from dotenv import load_dotenv
load_dotenv('/etc/pa_v2/secrets.env')

try:
    from services.email.providers.outlook_provider import OutlookGraphProvider
    
    print('📧 Checking BYU Outlook mailbox...')
    outlook = OutlookGraphProvider()
    
    if outlook.is_authenticated():
        result = outlook.get_latest_emails(count=5)
        
        if result.get('success'):
            emails = result.get('emails', [])
            print(f'📊 Found {len(emails)} emails in BYU Outlook mailbox')
            
            if len(emails) == 0:
                print('✅ BYU mailbox is EMPTY - redirects working perfectly!')
                print('💡 SAFE to remove Outlook timer checks')
            else:
                print('⚠️  BYU mailbox has emails - redirect may not be 100% reliable')
                print('📋 Recent emails in BYU mailbox:')
                for i, email in enumerate(emails, 1):
                    print(f'   {i}. From: {email.get(\"from\", \"Unknown\")[:40]}')
                    print(f'      Subject: {email.get(\"subject\", \"No subject\")[:60]}')
                    print(f'      Date: {email.get(\"date\", \"Unknown\")}')
                    print()
                print('🔄 RECOMMEND keeping Outlook timer as backup')
        else:
            print(f'❌ Error checking BYU mailbox: {result.get(\"message\")}')
    else:
        print('❌ BYU Outlook not authenticated')
        
except Exception as e:
    print(f'❌ Error: {e}')
"
