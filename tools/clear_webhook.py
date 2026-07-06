"""Telegram webhook ni o'chirish — BOT-MARKET/konstruktor pollingni bloklaganda."""

from __future__ import annotations

import asyncio
import os
import sys

from aiogram import Bot
from dotenv import load_dotenv

from telegram_polling_guard import ensure_polling_mode

load_dotenv()


async def main() -> None:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        print("BOT_TOKEN yo'q")
        sys.exit(1)
    bot = Bot(token=token)
    try:
        wh = await bot.get_webhook_info()
        had = bool(wh.url)
        print(f"Webhook: {wh.url or '(yoq)'}")
        await ensure_polling_mode(bot)
        print("Webhook o'chirildi." if had else "Webhook allaqachon yo'q.")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
