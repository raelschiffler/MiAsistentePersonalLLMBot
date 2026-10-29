import os
import shutil
from pathlib import Path
from datetime import datetime

LOG_DIR = Path("/var/log/llm-bot")
LOG_FILE = LOG_DIR / "llama_server.log"
MAX_DIR_SIZE = 50 * 1024 * 1024   # 50 MB
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
TRIM_KEEP = 5 * 1024 * 1024       # keep last 5 MB when trimming


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def rotate_on_start():
    """Call once at bot startup. Renames existing log if non-empty."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > 0:
        LOG_FILE.rename(LOG_DIR / f"llama_server_newSession_{_ts()}.log")


def rotate_on_stop():
    """Call on SIGTERM. Renames current log."""
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > 0:
        LOG_FILE.rename(LOG_DIR / f"llama_server_closedSession_{_ts()}.log")


def cleanup_old_logs():
    """Delete oldest rotated logs until directory total < 50 MB."""
    if not LOG_DIR.exists():
        return
    files = sorted(
        LOG_DIR.glob("llama_server_*.log"),
        key=lambda p: p.stat().st_mtime,
    )
    total = sum(f.stat().st_size for f in files)
    for f in files:
        if total <= MAX_DIR_SIZE:
            break
        total -= f.stat().st_size
        f.unlink()


def trim_current_log():
    """If llama_server.log > 10 MB, keep only the last 5 MB."""
    if not LOG_FILE.exists():
        return
    size = LOG_FILE.stat().st_size
    if size <= MAX_FILE_SIZE:
        return
    with open(LOG_FILE, "rb") as f:
        f.seek(size - TRIM_KEEP)
        tail = f.read()
    nl = tail.find(b"\n")
    if nl != -1:
        tail = tail[nl + 1:]
    with open(LOG_FILE, "wb") as f:
        f.write(tail)   
