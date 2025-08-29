"""Run webhook server."""
import os
import sys
import pathlib

# Add project root to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/etc/pa_v2/secrets.env')

# Import after setting up environment
try:
    import uvicorn
    from src.webhooks.app import app
    
    if __name__ == "__main__":
        port = int(os.getenv("WEBHOOK_PORT", "8080"))
        host = os.getenv("WEBHOOK_HOST", "0.0.0.0")
        
        print(f"🚀 Starting Gmail webhook server on {host}:{port}")
        uvicorn.run(app, host=host, port=port)
        
except ImportError as e:
    print(f"❌ Missing dependencies for webhook server: {e}")
    print("💡 Install with: pip install fastapi uvicorn")
    sys.exit(1)
