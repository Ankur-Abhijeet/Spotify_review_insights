import os
import json
from datetime import datetime
from backend.utils.logger import get_logger

logger = get_logger(__name__)

USAGE_FILE = os.path.join(os.getcwd(), "data", "usage.json")

_in_memory_usage = {}

def get_usage():
    today = datetime.now().strftime("%Y-%m-%d")
    default_usage = {"date": today, "tokens_used": 0, "requests_made": 0}

    # 1. Try to read from file first for persistence
    if os.path.exists(USAGE_FILE):
        try:
            with open(USAGE_FILE, 'r') as f:
                usage = json.load(f)
            if usage.get("date") == today:
                return usage
        except Exception:
            pass

    # 2. Fall back to in-memory tracker
    global _in_memory_usage
    if not _in_memory_usage or _in_memory_usage.get("date") != today:
        _in_memory_usage = default_usage

    return _in_memory_usage

def increment_usage(tokens: int, requests: int = 1):
    usage = get_usage()
    usage["tokens_used"] += tokens
    usage["requests_made"] += requests
    
    global _in_memory_usage
    _in_memory_usage = usage

    # Safely persist to file
    try:
        os.makedirs(os.path.dirname(USAGE_FILE), exist_ok=True)
        with open(USAGE_FILE, 'w') as f:
            json.dump(usage, f, indent=4)
    except Exception as e:
        logger.error(f"[UsageTracker] Error writing usage file: {e}")
