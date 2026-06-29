import json
import os
from typing import Any, Dict, List, Union

def read_json(file_path: str) -> Union[Dict, List, None]:
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading JSON from {file_path}: {e}")
        return None

def write_json(file_path: str, data: Union[Dict, List]) -> bool:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing JSON to {file_path}: {e}")
        return False
