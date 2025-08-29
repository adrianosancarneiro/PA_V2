"""Utilities to interact with the WhatsApp bridge script.

This module provides a minimal interface to the Node.js script located in
``scripts/whatsapp_bridge.js``. The real implementation would offer
bi-directional communication, but for testing we simply ensure the script
exists and can be launched.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

BRIDGE_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "whatsapp_bridge.js"


def launch_bridge(extra_args: Optional[list[str]] = None) -> subprocess.Popen:
    """Launch the Node.js WhatsApp bridge script.

    Returns the ``Popen`` object so callers can manage the process.
    """
    args = ["node", str(BRIDGE_SCRIPT)]
    if extra_args:
        args.extend(extra_args)
    return subprocess.Popen(args)
