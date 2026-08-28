"""Boshqa botlardan hub ga event (HTTP yoki Telegram)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

HUB_URL = (os.getenv("YORDAMCHI_HUB_URL", "").strip() or os.getenv("HUB_URL", "").strip()).rstrip("/")
HUB_SECRET = (
    os.getenv("YORDAMCHI_HUB_SECRET", "").strip()
    or os.getenv("HUB_SECRET", "").strip()
)
TG_BOT_TOKEN = os.getenv("YORDAMCHI_BOT_TOKEN", "").strip() or os.getenv("BOT_TOKEN", "").strip()
INGEST_CHAT_ID = int(
    (os.getenv("YORDAMCHI_INGEST_CHAT_ID", "").strip() or os.getenv("INGEST_CHAT_ID", "0").strip() or "0")
)
TZ = ZoneInfo(os.getenv("TZ", "Asia/Tashkent"))


def today_iso() -> str:
    return datetime.now(TZ).date().isoformat()


def hub_configured() -> bool:
    if HUB_URL and HUB_SECRET:
        return True
    if TG_BOT_TOKEN and INGEST_CHAT_ID:
        return True
    return False


def _post_http(payload: dict) -> bool:
    if not HUB_URL or not HUB_SECRET:
        return False
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{HUB_URL}/ingest",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Secret": HUB_SECRET,
            "Authorization": f"Bearer {HUB_SECRET}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        log.warning("Hub HTTP ingest HTTPError %s: %s", e.code, e.reason)
        return False
    except Exception as e:
        log.warning("Hub HTTP ingest failed: %s", e)
        return False


def _post_telegram(day: str, tg_id: int, bot_key: str, summary: str) -> bool:
    if not TG_BOT_TOKEN or not INGEST_CHAT_ID:
        return False
    text = f"HUB|{day}|{tg_id}|{bot_key}|{summary[:400]}"
    body = json.dumps(
        {"chat_id": INGEST_CHAT_ID, "text": text, "disable_notification": True}
    ).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception as e:
        log.warning("Hub Telegram ingest failed: %s", e)
        return False


def _send_sync(payload: dict, day: str, tg_id: int, bot_key: str, summary: str) -> tuple[bool, str]:
    if not hub_configured():
        return False, "Hub sozlanmagan (URL/SECRET yoki BOT_TOKEN/INGEST_CHAT_ID yo'q)"
    if _post_http(payload):
        return True, "HTTP"
    if _post_telegram(day, tg_id, bot_key, summary):
        return True, "Telegram"
    return False, "Yuborib bo'lmadi"


async def push_to_yordamchi_hub(
    *,
    tg_id: int,
    bot_key: str,
    summary: str = "",
    day_iso: str | None = None,
    event_type: str = "",
    user_name: str = "",
    activity_type: str = "",
    status: str = "",
    metadata: dict | None = None,
) -> tuple[bool, str]:
    text = " ".join(str(summary or "").split())
    et = str(event_type or "").strip().lower()
    if not tg_id:
        return False, "tg_id yo'q"
    if not text and not et:
        return False, "matn yoki event_type kerak"
    day = day_iso or today_iso()
    payload: dict = {
        "tg_id": int(tg_id),
        "bot_key": str(bot_key or "").strip().lower(),
        "day": day,
    }
    if text:
        payload["summary"] = text[:420]
    if et:
        payload["event_type"] = et
    if user_name:
        payload["user_name"] = str(user_name).strip()[:80]
    if activity_type:
        payload["activity_type"] = str(activity_type).strip().lower()[:32]
    if status:
        payload["status"] = str(status).strip().lower()[:16]
    if metadata:
        payload["metadata"] = metadata

    def _run() -> tuple[bool, str]:
        return _send_sync(payload, day, int(tg_id), payload["bot_key"], payload.get("summary", ""))

    try:
        return await asyncio.to_thread(_run)
    except Exception as e:
        log.debug("push_to_yordamchi_hub: %s", e)
        return False, str(e)[:80]


def push_to_yordamchi_hub_background(**kwargs) -> None:
    try:
        asyncio.get_running_loop().create_task(push_to_yordamchi_hub(**kwargs))
    except RuntimeError:
        pass


async def push_session_start(
    *,
    tg_id: int,
    bot_key: str,
    user_name: str = "",
    activity_type: str = "",
    status: str = "active",
    metadata: dict | None = None,
) -> tuple[bool, str]:
    return await push_to_yordamchi_hub(
        tg_id=tg_id,
        bot_key=bot_key,
        event_type="session_start",
        user_name=user_name,
        activity_type=activity_type,
        status=status,
        metadata=dict(metadata or {}),
    )


async def push_session_end(
    *,
    tg_id: int,
    bot_key: str,
    activity_type: str = "",
) -> tuple[bool, str]:
    return await push_to_yordamchi_hub(
        tg_id=tg_id,
        bot_key=bot_key,
        event_type="session_end",
        activity_type=activity_type,
    )


def push_session_start_background(**kwargs) -> None:
    try:
        asyncio.get_running_loop().create_task(push_session_start(**kwargs))
    except RuntimeError:
        pass


def push_session_end_background(**kwargs) -> None:
    try:
        asyncio.get_running_loop().create_task(push_session_end(**kwargs))
    except RuntimeError:
        pass
