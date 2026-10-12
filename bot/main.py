import logging

from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.request import HTTPXRequest

from .config import BOT_TOKEN, WHITELIST
from .handlers import on_start, on_text, on_other

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("tg-bot")

def main() -> None:
    request = HTTPXRequest(connect_timeout=30, read_timeout=60, write_timeout=60)
    app = Application.builder().token(BOT_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_handler(MessageHandler(~filters.TEXT & ~filters.COMMAND, on_other))

    log.info("Bot starting. Whitelist size: %d", len(WHITELIST))
    app.run_polling()

if __name__ == "__main__":
    main()   
