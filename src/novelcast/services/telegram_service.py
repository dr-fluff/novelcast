import asyncio
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


class TelegramService:
    """
    Robust Telegram integration:
    - safe startup
    - retry limits
    - graceful disable on fatal auth errors
    """

    def __init__(self, settings_service, story_service, download_service):
        self.settings = settings_service
        self.stories = story_service
        self.downloads = download_service

        self._task: Optional[asyncio.Task] = None
        self._offset = 0

        self._disabled = False  # <- permanent kill switch after fatal errors
        self._consecutive_failures = 0
        self._max_failures = 5

    # ─────────────────────────────
    # CONFIG
    # ─────────────────────────────

    def _tg(self) -> dict:
        return self.settings.get_resolved_server_settings().get("telegram", {})

    def _token(self) -> Optional[str]:
        return self._tg().get("bot_token")

    def _chat_id(self) -> Optional[str]:
        return self._tg().get("chat_id")

    def _enabled(self) -> bool:
        if self._disabled:
            return False
        cfg = self._tg()

        return (
            not self._disabled
            and cfg.get("enabled") is True
            and bool(self._token())
            and bool(self._chat_id())
        )
    

    def _url(self, method: str) -> str:
        return TELEGRAM_API.format(token=self._token(), method=method)

    # ─────────────────────────────
    # LIFECYCLE
    # ─────────────────────────────

    def start(self):
        if not self._enabled():
            logger.info("Telegram disabled (missing config or disabled flag)")
            return

        if self._task is None:
            self._task = asyncio.create_task(self._poll_loop())
            logger.info("Telegram polling started")

    def stop(self):
        if self._task:
            self._task.cancel()
            self._task = None
            logger.info("Telegram polling stopped")
    
    def restart(self):
        # only restart if not permanently disabled
        if self._disabled:
            logger.warning("Telegram is disabled permanently; restart blocked")
            return

        self.stop()
        self._consecutive_failures = 0
        self.start()

    # ─────────────────────────────
    # CORE LOOP
    # ─────────────────────────────

    async def _poll_loop(self):
        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                try:
                    await self._poll_once(client)
                    self._consecutive_failures = 0  # reset on success

                except asyncio.CancelledError:
                    break

                except Exception as e:
                    self._consecutive_failures += 1
                    logger.warning(
                        "Telegram poll error (%d/%d): %s",
                        self._consecutive_failures,
                        self._max_failures,
                        e,
                    )

                    # 🔴 Hard stop if too many failures
                    if self._consecutive_failures >= self._max_failures:
                        logger.error("Telegram disabled after repeated failures")
                        self._disabled = True
                        break

                    await asyncio.sleep(min(30, 2 ** self._consecutive_failures))

    async def _poll_once(self, client: httpx.AsyncClient):
        if not self._enabled():
            return

        r = await client.get(
            self._url("getUpdates"),
            params={
                "offset": self._offset,
                "timeout": 30,
                "allowed_updates": ["message"],
            },
        )

        # ── IMPORTANT: handle auth failure cleanly ──
        if r.status_code in (401, 403):
            logger.error(
                "Telegram auth failed (%s). Disabling bot.",
                r.status_code,
            )
            self._disabled = True
            return

        data = r.json()

        if not data.get("ok"):
            logger.warning("Telegram API error: %s", data)
            return

        for update in data["result"]:
            self._offset = update["update_id"] + 1
            await self._handle_update(update)

    # ─────────────────────────────
    # HANDLER
    # ─────────────────────────────

    async def _handle_update(self, update: dict):
        msg = update.get("message", {})
        text = msg.get("text", "").strip()
        chat_id = str(msg.get("chat", {}).get("id", ""))

        if chat_id != self._chat_id():
            return

        if text.startswith("/status"):
            await self.send_message("✅ NovelCast is running.")

        elif text.startswith("/stories"):
            stories = await self.stories.list_stories(limit=10)
            lines = [f"📚 {s.title} — {s.chapter_count}" for s in stories]
            await self.send_message("\n".join(lines) or "No stories")

        else:
            await self.send_message("Commands: /status /stories /download <url>")

    # ─────────────────────────────
    # OUTBOUND
    # ─────────────────────────────

    async def send_message(self, text: str):
        if not self._enabled():
            return

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    self._url("sendMessage"),
                    json={
                        "chat_id": self._chat_id(),
                        "text": text,
                        "parse_mode": "Markdown",
                    },
                )
        except Exception as e:
            logger.warning("Telegram send failed: %s", e)

    # ─────────────────────────────
    # TEST
    # ─────────────────────────────

    async def send_test(self) -> tuple[bool, str]:
        if not self._token() or not self._chat_id():
            return False, "Missing token or chat_id"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    self._url("sendMessage"),
                    json={
                        "chat_id": self._chat_id(),
                        "text": "👋 Telegram integration OK",
                    },
                )

            data = r.json()

            if r.status_code == 401:
                self._disabled = True
                return False, "Invalid bot token (401 Unauthorized)"

            if data.get("ok"):
                return True, "OK"

            return False, data.get("description", "Unknown error")

        except Exception as e:
            return False, str(e)
    
    def notify_story_added(self, title: str, author: str | None):
        asyncio.create_task(self.send_message(
            f"📖 *New story added*\n{title}"
            + (f" by _{author}_" if author else "")
        ))

    def notify_story_updated(self, title: str, author: str | None, new_chapters: int):
        asyncio.create_task(self.send_message(
            f"🔄 *Story updated*\n{title}"
            + (f" by _{author}_" if author else "")
            + f"\n+{new_chapters} new chapter{'s' if new_chapters != 1 else ''}"
        ))

    def notify_story_deleted(self, title: str):
        asyncio.create_task(self.send_message(
            f"🗑️ *Story deleted*\n{title}"
        ))