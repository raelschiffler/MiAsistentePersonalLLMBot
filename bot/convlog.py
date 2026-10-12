import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .config import DATA_DIR

log = logging.getLogger("tg-bot.convlog")
CONV_DIR = DATA_DIR / "conversations"

def log_message(user_id: int, role: str, content: str) -> None:
    """Append one message to the user's conversation log."""
    path = CONV_DIR / f"{user_id}.jsonl"
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "content": content[:2000],
    }
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")

def read_conversation(user_id: int, last_n: int = 50) -> str:
    """Return last N messages as readable text (for main user's on-demand review)."""
    path = CONV_DIR / f"{user_id}.jsonl"
    if not path.exists():
        return "(no conversation recorded)"
    lines = path.read_text().strip().splitlines()
    recent = lines[-last_n:]
    out = []
    for line in recent:
        e = json.loads(line)
        out.append(f"[{e['ts'][:16]}] {e['role']}: {e['content'][:300]}")
    return "\n".join(out)   
