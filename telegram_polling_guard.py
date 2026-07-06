"""BOT-MARKET / bot-konstruktor webhookini o'chirish — barcha botlar uchun.

Nusxa: har bir bot repoga ko'chiriladi (import uchun shu repoda bo'lishi kerak).
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


async def ensure_polling_mode(bot, *, drop_pending: bool = True) -> None:
    """Webhook bo'lsa o'chiradi — faqat bizning polling ishlashi uchun."""
    me = await bot.get_me()
    wh = await bot.get_webhook_info()
    log.info("Telegram bot: @%s (id=%s)", me.username, me.id)
    if wh.url:
        log.warning(
            "Webhook topildi (%s) — o'chirilmoqda (BOT-MARKET/konstruktor)",
            wh.url,
        )
        await bot.delete_webhook(drop_pending_updates=drop_pending)
    else:
        log.info("Webhook yo'q — polling rejimi")
