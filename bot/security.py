import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .config import DATA_DIR, MAIN_USER_ID

log = logging.getLogger("tg-bot.security")
LOG_PATH = DATA_DIR / "security_log.jsonl"

def log_security_event(user_id: int, username: str, text: str, reason: str) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "username": username,
        "text": text[:500],
        "reason": reason,
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")

def read_security_log(last_n: int = 15) -> str:
    if not LOG_PATH.exists():
        return "(no security events recorded)"
    lines = LOG_PATH.read_text().strip().splitlines()
    recent = lines[-last_n:]
    return "\n".join(recent) if recent else "(no security events recorded)"

async def notify_main_user(context, user_id: int, username: str, text: str) -> None:
    from .config import CONTACTS
    name = CONTACTS.get(str(user_id), f"@{username}")
    alert = (
        f"⚠️ Unauthorized access attempt\n"
        f"User: {name} (ID: {user_id})\n"
        f"Message: {text[:200]}"
    )
    try:
        await context.bot.send_message(chat_id=MAIN_USER_ID, text=alert)
    except Exception as e:
        log.error("Failed to notify main user: %s", e)   
