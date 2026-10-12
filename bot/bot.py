	#!/usr/bin/env python3
"""
Personal Telegram LLM bot.
- Whitelist-gated access
- Security log for unauthorized attempts
- Main user can ask the LLM about the log naturally
- No code execution path exists (thin HTTP proxy to local llama-server)
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
WHITELIST_PATH = BASE_DIR / "whitelist.json"
LOG_PATH = BASE_DIR / "security_log.jsonl"

# ─── Load config ──────────────────────────────────────────────────────────────
logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("tg-bot")

with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

with open(WHITELIST_PATH) as f:
    WHITELIST: set[int] = set(json.load(f))

BOT_TOKEN = CONFIG["bot_token"]
MAIN_USER_ID: int = CONFIG["main_user_id"]
LLAMA_URL: str = CONFIG["llama_url"]
MAX_HISTORY: int = CONFIG.get("max_history", 10)

# ─── Security log helpers ─────────────────────────────────────────────────────

def log_security_event(user_id: int, username: str, text: str, reason: str) -> None:
    """Append one JSON line to the security log."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "username": username,
        "text": text[:500],  # cap to avoid bloat
        "reason": reason,
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")

def read_security_log(last_n: int = 20) -> str:
    """Return the last N log entries as a readable string (for LLM context)."""
    if not LOG_PATH.exists():
        return "(no security events recorded)"
    lines = LOG_PATH.read_text().strip().splitlines()
    recent = lines[-last_n:]
    return "\n".join(recent) if recent else "(no security events recorded)"

# ─── LLM call ─────────────────────────────────────────────────────────────────
# Model-agnostic bot, just a pass-through:
async def call_llama(messages: list[dict]) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{LLAMA_URL}/v1/chat/completions",
                json={"messages": messages},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except (httpx.ConnectError, httpx.ConnectTimeout):
        return None
    except Exception as e:
        log.warning("LLM call failed: %s", e)
        return None   

#async def call_llama(messages: list[dict]) -> str | None:
#    """Send chat messages to llama-server. Returns response text or None if server is down."""
#    try:
#        async with httpx.AsyncClient(timeout=120) as client:
#            resp = await client.post(
#                f"{LLAMA_URL}/v1/chat/completions",
#                json={
#                    "messages": messages,
#                    "max_tokens": 512,
#                    "temperature": 0.7,
#                    "repeat_penalty": 1.5,
#                },
#            )
#            resp.raise_for_status()
#            data = resp.json()
#            return data["choices"][0]["message"]["content"].strip()
#    except (httpx.ConnectError, httpx.ConnectTimeout):
#        return None
#    except Exception as e:
#        log.warning("LLM call failed: %s", e)
#        return None
#
# ─── System prompt builder ────────────────────────────────────────────────────

def build_system_prompt(user_id: int) -> str | None:
    base = CONFIG.get("system_prompt", "")
    if not base:
        base = "You are a helpful personal assistant. Be concise. Answer in the user's language."
    if user_id == MAIN_USER_ID:
        log_content = read_security_log(15)
        base += (
            "\n\nSECURITY LOG (last 15 entries):\n"
            f"{log_content}\n"
            "If the user asks about the security log or unauthorized access, summarize the entries above."
        )
    return base   

#def build_system_prompt(user_id: int) -> str:
#    base = (
#        "You are a helpful personal assistant running on a local LLM. "
#        "Be concise. Answer in the user's language."
#    )
#    if user_id == MAIN_USER_ID:
#        log_content = read_security_log(15)
#        base += (
#            "\n\nSECURITY LOG (last 15 entries, JSON lines):\n"
#            f"{log_content}\n\n"
#            "If the user asks about the security log, unauthorized access, or who tried to use the bot, "
#            "summarize the relevant entries from the log above in plain language."
#        )
#    return base
#
# ─── Handlers ─────────────────────────────────────────────────────────────────

async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    username = user.username or "unknown"
    log.info("/start from user_id=%s username=%s", user_id, username)

    if user_id not in WHITELIST:
        log_security_event(user_id, username, "/start", "unauthorized /start attempt")
#        await notify_main_user(user_id, username, "/start")
        await notify_main_user(context, user_id, username, "/start")
        # Do NOT reply to unauthorized users (no confirmation of existence)
        return

    # Reset conversation history for this user
    context.user_data["history"] = []
    await update.message.reply_text("Hey! I'm up. Send me a message and I'll talk to the model.")

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    username = user.username or "unknown"
    text = update.message.text

    if user_id not in WHITELIST:
        log_security_event(user_id, username, text, "unauthorized message")
        await notify_main_user(context, user_id, username, text)
        return

    # Build message history
    history: list[dict] = context.user_data.setdefault("history", [])
    history.append({"role": "user", "content": text})

    # Keep history bounded
    if len(history) > MAX_HISTORY * 2:
        del history[: len(history) - MAX_HISTORY * 2]

    # Compose full prompt
    sys_prompt = build_system_prompt(user_id)
    messages = []
    if sys_prompt:
        messages.append({"role": "system", "content": sys_prompt})
    messages.extend(history)   
#    messages = [{"role": "system", "content": build_system_prompt(user_id)}]
#    messages.extend(history)

    # Call LLM
    reply = await call_llama(messages)

    if reply is None:
        await update.message.reply_text(
            "The model server seems to be down right now. "
            "I'll be back once it's loaded again. Sorry about that!"
        )
        return

    # Append assistant reply to history
    history.append({"role": "assistant", "content": reply})

    # Truncate to first 2 sentences (mitigates Llama 3.1 rambling)
    #reply = truncate_sentences(reply, 2)

    n_sent = CONFIG.get("truncate_sentences", 0)
    if n_sent > 0:
        reply = truncate_sentences(reply, n_sent)   

    # Telegram message limit is 4096 chars
    if len(reply) > 4096:
        reply = reply[:4093] + "..."

#    await update.message.reply_text(reply)
    for attempt in range(3):
        try:
            await update.message.reply_text(reply)
            break
        except Exception as e:
            log.warning("Reply attempt %d failed: %s", attempt + 1, e)
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)  # 1s, 2s   

async def notify_main_user(context: ContextTypes.DEFAULT_TYPE, user_id: int, username: str, text: str) -> None:
    alert = (
        f"⚠️ Unauthorized access attempt\n"
        f"User ID: {user_id}\n"
        f"Username: @{username}\n"
        f"Message: {text[:200]}"
    )
    try:
        await context.bot.send_message(chat_id=MAIN_USER_ID, text=alert)
    except Exception as e:
        log.error("Failed to notify main user: %s", e)   

#async def notify_main_user(user_id: int, username: str, text: str) -> None:
#    """Send an alert to the main user about an unauthorized interaction attempt."""
#    app: Application = Application.instance
#    alert = (
#        f"⚠️ Unauthorized access attempt\n"
#        f"User ID: {user_id}\n"
#        f"Username: @{username}\n"
#        f"Message: {text[:200]}"
#    )
#    try:
#        await app.bot.send_message(chat_id=MAIN_USER_ID, text=alert)
#    except Exception as e:
#        log.error("Failed to notify main user: %s", e)

def truncate_sentences(text: str, n: int) -> str:
    """Keep only the first n sentences (simple heuristic)."""
    import re
    parts = re.split(r'(?<=[.!?])\s+', text)
    return " ".join(parts[:n])

# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    # Catch-all for non-text, non-command messages from unauthorized users
    async def on_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if user and user.id not in WHITELIST:
            log_security_event(user.id, user.username or "unknown", "(non-text message)", "unauthorized non-text")
            await notify_main_user(context, user.id, user.username or "unknown", "(non-text message)")

    app.add_handler(MessageHandler(~filters.TEXT & ~filters.COMMAND, on_other))

    log.info("Bot starting. Whitelist size: %d", len(WHITELIST))
    app.run_polling()

if __name__ == "__main__":
    main()   
