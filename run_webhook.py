#!/usr/bin/env python3
"""Direct webhook runner with proper path setup."""
import os
import sys
import pathlib

# Add project root and src to path for proper imports
project_root = pathlib.Path(__file__).resolve().parent
src_path = project_root / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_path))

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/etc/pa_v2/secrets.env')

try:
    import uvicorn
    
    # Import the app with the correct path structure
    sys.path.insert(0, str(src_path / "webhooks"))
    from app import app
    
    if __name__ == "__main__":
        port = int(os.getenv("WEBHOOK_PORT", "8080"))
        host = os.getenv("WEBHOOK_HOST", "0.0.0.0")
        
        print(f"🚀 Starting Gmail webhook server on {host}:{port}")
        uvicorn.run(app, host=host, port=port)
        
except ImportError as e:
    print(f"❌ Missing dependencies for webhook server: {e}")
    print("💡 Install with: pip install fastapi uvicorn")
    sys.exit(1)
