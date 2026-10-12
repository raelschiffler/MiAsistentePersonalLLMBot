import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from .config import WHITELIST, MAIN_USER_ID, MAX_HISTORY
from .llama import get_reply
from .security import log_security_event, read_security_log, notify_main_user
from .contacts import record_interaction
from .convlog import log_message, read_conversation

log = logging.getLogger("tg-bot.handlers")

async def _safe_reply(message, text: str) -> None:
    for attempt in range(3):
        try:
            await message.reply_text(text)
            return
        except Exception as e:
            log.warning("Reply attempt %d failed: %s", attempt + 1, e)
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)

async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    username = user.username or "unknown"
    log.info("/start from user_id=%s username=%s", user_id, username)

    if user_id not in WHITELIST:
        log_security_event(user_id, username, "/start", "unauthorized /start")
        await notify_main_user(context, user_id, username, "/start")
        return

    context.user_data["history"] = []
    record_interaction(user_id)
    log_message(user_id, "user", "/start")
    await _safe_reply(update.message, "Hey! I'm up. Send me a message and I'll talk to the model.")

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    username = user.username or "unknown"
    text = update.message.text

    if user_id not in WHITELIST:
        log_security_event(user_id, username, text, "unauthorized message")
        await notify_main_user(context, user_id, username, text)
        return

    record_interaction(user_id)
    log_message(user_id, "user", text)

    history: list[dict] = context.user_data.setdefault("history", [])
    history.append({"role": "user", "content": text})
    if len(history) > MAX_HISTORY * 2:
        del history[: len(history) - MAX_HISTORY * 2]

    # Build extra system prompt for main user (security log + interaction report)
    extra = ""
    if user_id == MAIN_USER_ID:
        extra = (
            f"SECURITY LOG (last 15):\n{read_security_log(15)}\n\n"
            f"If asked about the security log, unauthorized access, or who tried to use the bot, summarize the entries above."
        )

    reply = await get_reply(text, history, user_id, system_prompt_extra=extra)

    if reply is None:
        await _safe_reply(update.message, "The model server seems to be down right now. I'll be back once it's loaded again.")
        return

    history.append({"role": "assistant", "content": reply})
    log_message(user_id, "assistant", reply)

    if len(reply) > 4096:
        reply = reply[:4093] + "..."

    await _safe_reply(update.message, reply)

async def on_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user and user.id not in WHITELIST:
        log_security_event(user.id, user.username or "unknown", "(non-text)", "unauthorized non-text")
        await notify_main_user(context, user.id, user.username or "unknown", "(non-text)")   
