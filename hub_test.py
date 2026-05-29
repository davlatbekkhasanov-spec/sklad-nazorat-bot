"""Admin: hub test."""

from __future__ import annotations

import os

from aiogram.types import Message

from yordamchi_push import push_to_yordamchi_hub

BTN_HUB_TEST = "🧪 Test (admin)"
_ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or "0")


def is_admin(user_id: int) -> bool:
    return _ADMIN_ID and user_id == _ADMIN_ID


async def handle_admin_hub_test(message: Message) -> None:
    uid = message.from_user.id if message.from_user else 0
    if not is_admin(uid):
        return await message.answer("Faqat admin uchun.")

    ok, via = await push_to_yordamchi_hub(
        tg_id=uid,
        bot_key="sklad",
        summary="[TEST] Papka A-12: sanaldi OK, kun 3/10",
    )
    await message.answer(
        f"{'✅' if ok else '❌'} Sklad → yordamchi hub ({via})\n"
        "Endi davlat-yordamchi botda ✅ Якунлаш yuboring."
    )
