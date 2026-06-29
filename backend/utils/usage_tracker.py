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
