import json
import logging
from pathlib import Path

log = logging.getLogger("tg-bot.groups")

GROUPS_FILE = Path(__file__).parent.parent / "data" / "groups.json"


def load_groups() -> dict:
    try:
        return json.loads(GROUPS_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_groups(groups: dict) -> None:
    GROUPS_FILE.parent.mkdir(parents=True, exist_ok=True)
    GROUPS_FILE.write_text(json.dumps(groups, indent=2))


def add_group(chat_id: int, title: str, added_by: str, member_count: int) -> None:
    groups = load_groups()
    groups[str(chat_id)] = {
        "title": title,
        "added_by": added_by,
        "member_count": member_count,
        "authorized": False,
    }
    save_groups(groups)
    log.info("Group added to tracking: %s (id=%s) by %s", title, chat_id, added_by)


def authorize_group(chat_id: int) -> None:
    groups = load_groups()
    if str(chat_id) in groups:
        groups[str(chat_id)]["authorized"] = True
        save_groups(groups)
        log.info("Group authorized: %s (id=%s)", groups[str(chat_id)]["title"], chat_id)


def deny_group(chat_id: int) -> None:
    groups = load_groups()
    if str(chat_id) in groups:
        groups[str(chat_id)]["authorized"] = False
        save_groups(groups)
        log.info("Group denied: %s (id=%s)", groups[str(chat_id)]["title"], chat_id)


def is_authorized(chat_id: int) -> bool:
    groups = load_groups()
    return groups.get(str(chat_id), {}).get("authorized", False)   
