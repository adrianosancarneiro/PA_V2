#!/usr/bin/env python3
"""Gmail push lifecycle renewal script for systemd."""
import sys
import pathlib
import os

# Add src to path
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))

# Load environment
from dotenv import load_dotenv
load_dotenv('/etc/pa_v2/secrets.env')

# Run the renewal
from jobs.push_lifecycle import run

if __name__ == "__main__":
    run()
