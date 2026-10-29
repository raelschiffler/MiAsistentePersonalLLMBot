import json
import logging
from pathlib import Path

from .config import DATA_DIR

log = logging.getLogger("tg-bot.memory")
MEMORY_PATH = DATA_DIR / "memory.json"


def load_memory() -> list[str]:
    try:
        return json.loads(MEMORY_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_memory(facts: list[str]) -> None:
    MEMORY_PATH.write_text(json.dumps(facts, ensure_ascii=False, indent=2))


def add_fact(fact: str) -> list[str]:
    facts = load_memory()
    facts.append(fact)
    save_memory(facts)
    return facts


def remove_fact(index: int) -> list[str] | None:
    facts = load_memory()
    if 0 <= index < len(facts):
        facts.pop(index)
        save_memory(facts)
        return facts
    return None


def get_memory_block() -> str:
    """Return a formatted block for injection into the system prompt."""
    facts = load_memory()
    if not facts:
        return ""
    lines = "\n".join(f"- {f}" for f in facts)
    return f"\n\nUSER'S PERSISTENT MEMORY (facts the user told you to remember):\n{lines}\nUse these facts when relevant. Do not mention this list unless asked."   
