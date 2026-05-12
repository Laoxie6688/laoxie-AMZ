#!/usr/bin/env python3
"""Check local prerequisites for Amazon Rufus QA collection."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import urllib.error
import urllib.request


def command_status(name: str) -> str:
    path = shutil.which(name)
    return f"OK: {path}" if path else "MISSING"


def chrome_status() -> str:
    candidates = [
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return f"OK: {candidate}"
    return "MISSING"


def cdp_status(base_url: str = "http://127.0.0.1:9222") -> str:
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/json/version", timeout=2) as response:
            data = json.load(response)
    except urllib.error.URLError as exc:
        return f"UNREACHABLE: {exc}"
    except Exception as exc:  # noqa: BLE001 - diagnostic script
        return f"ERROR: {exc}"

    browser = data.get("Browser", "unknown browser")
    websocket = data.get("webSocketDebuggerUrl")
    return f"OK: {browser}, websocket={websocket or 'missing'}"


def main() -> int:
    print("Amazon Rufus QA environment")
    print(f"python: {sys.executable}")
    print(f"chrome: {chrome_status()}")
    print(f"browser-harness: {command_status('browser-harness')}")
    print(f"chrome-cdp: {cdp_status()}")
    print()
    print("If Chrome CDP is unreachable, launch Chrome with:")
    print("  google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-profile")
    print("On macOS, use the Chrome binary inside /Applications with the same flags.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
