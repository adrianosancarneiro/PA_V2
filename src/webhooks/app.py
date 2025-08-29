"""FastAPI webhook app for Gmail push notifications."""
from fastapi import FastAPI, Request, Response
from base64 import b64decode
import json
import os
import sys
import pathlib

# Add project root to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

# Import with relative paths from the src directory
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from repo.push_repo import PushRepo
from webhooks.svc import gmail_process_history

app = FastAPI()
push = PushRepo()


@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "gmail-webhook"}


@app.post("/hooks/gmail")
async def gmail_hook(req: Request):
    """
    Handle Gmail push notification webhooks.
    
    Expects Google Cloud Pub/Sub message format:
    {
        "message": {
            "data": "<base64-encoded-json>",
            "messageId": "...",
            "publishTime": "..."
        }
    }
    """
    try:
        envelope = await req.json()
        message = (envelope or {}).get("message", {})
        data_b64 = message.get("data")
        
        if not data_b64:
            print("⚠️ No data in Gmail webhook message")
            return {"ok": True}
        
        # Update last pubsub timestamp
        push.touch_pubsub()
        
        # Decode the notification data
        data = json.loads(b64decode(data_b64).decode("utf-8"))
        history_id = int(data.get("historyId"))
        email_address = data.get("emailAddress")
        
        print(f"📨 Gmail webhook: historyId={history_id}, email={email_address}")
        
        # Process the history changes
        await gmail_process_history(history_id)
        
        return {"ok": True}
        
    except Exception as e:
        print(f"❌ Error processing Gmail webhook: {e}")
        push.set_push_state("gmail", "degraded")
        return {"error": str(e)}, 500


@app.post("/hooks/gmail/test")
async def gmail_test_hook():
    """Test endpoint for Gmail webhooks."""
    print("🧪 Gmail webhook test called")
    push.touch_pubsub()
    return {"ok": True, "message": "Test webhook received"}
