"""BOT-MARKET / bot-konstruktor webhookini o'chirish — barcha botlar uchun.

Nusxa: har bir bot repoga ko'chiriladi (import uchun shu repoda bo'lishi kerak).
"""
from __future__ import annotations

import asyncio
import logging

log = logging.getLogger(__name__)

WEBHOOK_WATCH_INTERVAL_SEC = 300


async def ensure_polling_mode(bot, *, drop_pending: bool = True) -> None:
    """Webhook bo'lsa o'chiradi — faqat bizning polling ishlashi uchun."""
    me = await bot.get_me()
    wh = await bot.get_webhook_info()
    log.info(
        "Telegram bot: @%s (id=%s) webhook=%s pending=%s",
        me.username,
        me.id,
        wh.url or "(yoq)",
        wh.pending_update_count,
    )
    if wh.url:
        log.warning(
            "Webhook topildi (%s) — o'chirilmoqda (BOT-MARKET/konstruktor)",
            wh.url,
        )
        await bot.delete_webhook(drop_pending_updates=drop_pending)
        wh2 = await bot.get_webhook_info()
        log.info("Webhook after delete: url=%s", wh2.url or "(yoq)")
    else:
        log.info("Webhook yo'q — polling rejimi")


async def webhook_watchdog(bot, *, interval_sec: int = WEBHOOK_WATCH_INTERVAL_SEC) -> None:
    """Webhook qayta o'rnatilsa (BOT-MARKET), polling uchun avtomatik tozalaydi."""
    while True:
        await asyncio.sleep(interval_sec)
        try:
            await ensure_polling_mode(bot, drop_pending=False)
        except Exception:
            log.exception("webhook_watchdog xato")
