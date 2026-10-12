import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
(DATA_DIR / "conversations").mkdir(exist_ok=True)

def _load(path: Path) -> dict | list:
    with open(path) as f:
        return json.load(f)

CONFIG = _load(CONFIG_DIR / "config.json")
WHITELIST: set[int] = set(_load(CONFIG_DIR / "whitelist.json"))
CONTACTS: dict[str, str] = {str(k): v for k, v in _load(CONFIG_DIR / "contacts.json").items()}

BOT_TOKEN = CONFIG["bot_token"]
MAIN_USER_ID: int = CONFIG["main_user_id"]
LLAMA_URL: str = CONFIG["llama_url"]
MAX_HISTORY: int = CONFIG.get("max_history", 20)
SYSTEM_PROMPT: str = CONFIG.get("system_prompt", "")
TRUNCATE_SENTENCES: int = CONFIG.get("truncate_sentences", 0)   
