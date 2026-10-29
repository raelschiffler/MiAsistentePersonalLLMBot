import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .config import DATA_DIR

log = logging.getLogger("tg-bot.reminders")
REMINDERS_PATH = DATA_DIR / "reminders.json"


def load_reminders() -> list[dict]:
    try:
        return json.loads(REMINDERS_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_reminders(reminders: list[dict]) -> None:
    REMINDERS_PATH.write_text(json.dumps(reminders, ensure_ascii=False, indent=2))


def add_reminder(chat_id: int, fire_at: str, text: str) -> None:
    reminders = load_reminders()
    reminders.append({"chat_id": chat_id, "fire_at": fire_at, "text": text})
    save_reminders(reminders)


def remove_reminder(index: int) -> None:
    reminders = load_reminders()
    if 0 <= index < len(reminders):
        reminders.pop(index)
        save_reminders(reminders)


def get_pending() -> list[dict]:
    """Return reminders that haven't fired yet (fire_at > now)."""
    now = datetime.now(timezone.utc).isoformat()
    return [r for r in load_reminders() if r["fire_at"] > now]   
