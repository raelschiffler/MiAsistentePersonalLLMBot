import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .config import DATA_DIR, CONTACTS, MAIN_USER_ID

log = logging.getLogger("tg-bot.contacts")
INTERACTIONS_PATH = DATA_DIR / "interactions.json"

def _load_interactions() -> dict:
    if INTERACTIONS_PATH.exists():
        with open(INTERACTIONS_PATH) as f:
            return json.load(f)
    return {}

def _save_interactions(data: dict) -> None:
    with open(INTERACTIONS_PATH, "w") as f:
        json.dump(data, f, indent=2)

def record_interaction(user_id: int) -> None:
    data = _load_interactions()
    key = str(user_id)
    if key not in data:
        data[key] = {"count": 0, "last": None}
    data[key]["count"] += 1
    data[key]["last"] = datetime.now(timezone.utc).isoformat()
    _save_interactions(data)

def get_report() -> str:
    """Return a human-readable report of all interactions."""
    data = _load_interactions()
    if not data:
        return "No interactions recorded yet."

    lines = ["📊 **Interaction Report**\n"]
    for uid, info in sorted(data.items(), key=lambda x: x[1]["count"], reverse=True):
        name = CONTACTS.get(uid, f"Unknown ({uid})")
        last = info["last"][:16].replace("T", " ") if info["last"] else "never"
        lines.append(f"• {name} — {info['count']} messages, last: {last} UTC")

    return "\n".join(lines)   
