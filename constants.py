
import os
import sys
import json

APP_VERSION = "2026.01.02"
GITHUB_REPO = "nununuuuu/MULTIDownload"
DEFAULT_APPEARANCE_MODE = "System"

# Language Map
CODE_TO_NAME = {'zh-TW': '繁體中文 (預設)', 'en': 'English'}

try:
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        # Assuming constants.py is in root
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # [Modified] Look in data directory
    lang_file = os.path.join(base_path, 'data', 'languages.json')
    
    if os.path.exists(lang_file):
        with open(lang_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                CODE_TO_NAME.update(data)
except Exception:
    pass
