import asyncio
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


class TelegramService:

    def __init__(self, settings_service, story_service, download_service):
        self.settings = settings_service
        self.stories = story_service
        self.downloads = download_service

        self._task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._offset = 0

        self._disabled = False
        self._consecutive_failures = 0
        self._max_failures = 5

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
            str(cfg.get("enabled", "")).strip().lower() in ("1", "true", "yes")
            and bool(self._token())
            and bool(self._chat_id())
        )
    
    def _url(self, method: str) -> str:
        return TELEGRAM_API.format(token=self._token(), method=method)

    def start(self):
        if not self._enabled():
            logger.info(
                "Telegram disabled (enabled=%s token=%s chat_id=%s)",
                self._tg().get("enabled"),
                bool(self._token()),
                bool(self._chat_id()),
            )
            return

        if self._task is not None:
            logger.debug("Telegram polling already running")
            return

        try:
            self._loop = asyncio.get_running_loop()
            self._task = self._loop.create_task(self._poll_loop())

            logger.info(
                "Telegram polling started (chat_id=%s)",
                self._chat_id(),
            )

        except RuntimeError:
            logger.exception(
                "Failed to start Telegram service: no running event loop"
            )

        if self._task is None:
            self._task = asyncio.create_task(self._poll_loop())
            logger.info("Telegram polling started")

    def stop(self):
        if not self._task:
            return

        logger.info("Stopping Telegram polling")

        self._task.cancel()

        self._task = None
        self._loop = None
    
    def restart(self):
        # only restart if not permanently disabled
        if self._disabled:
            logger.warning("Telegram is disabled permanently; restart blocked")
            return

        self.stop()
        self._consecutive_failures = 0
        self.start()

    
    def _handle_task_result(self, task: asyncio.Task):
        try:
            task.result()

        except asyncio.CancelledError:
            logger.debug("Telegram background task cancelled")

        except Exception:
            logger.exception("Telegram background task failed")


    def _fire_and_forget(self, coro):
        if self._disabled:
            logger.debug(
                "Telegram notification skipped because service is disabled"
            )
            return

        if self._loop is None:
            logger.warning(
                "Telegram notification skipped: no event loop registered"
            )
            return

        if self._loop.is_closed():
            logger.warning(
                "Telegram notification skipped: event loop closed"
            )
            return

        try:
            task = self._loop.create_task(coro)
            task.add_done_callback(self._handle_task_result)

        except Exception:
            logger.exception(
                "Failed to schedule Telegram notification"
            )
    
    async def _poll_loop(self):
        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                try:
                    await self._poll_once(client)
                    self._consecutive_failures = 0  # reset on success

                except asyncio.CancelledError:
                    logger.info("Telegram polling cancelled")
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

    async def send_message(self, text: str):
        logger.info("Telegram message: %s", text)
        if not self._enabled():
            logger.debug(
                "Skipping telegram send because service is disabled"
            )
            return

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    self._url("sendMessage"),
                    json={
                        "chat_id": self._chat_id(),
                        "text": text,
                        "parse_mode": "Markdown",
                    },
                )

            if r.status_code in (401, 403):
                logger.error(
                    "Telegram authentication failed (%s). Disabling service.",
                    r.status_code,
                )
                self._disabled = True
                return

            r.raise_for_status()

            data = r.json()

            if not data.get("ok"):
                logger.warning(
                    "Telegram API rejected message: %s",
                    data,
                )

        except httpx.TimeoutException:
            logger.warning("Telegram send timed out")

        except httpx.HTTPError:
            logger.exception("Telegram HTTP error")

        except Exception:
            logger.exception("Unexpected Telegram send failure")

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
        self._fire_and_forget(
            self.send_message(
                f"📖 *New story added*\n{title}"
                + (f" by _{author}_" if author else "")
            )
        )

    def notify_story_updated(
        self,
        title: str,
        author: str | None,
        new_chapters: int,
    ):
        self._fire_and_forget(
            self.send_message(
                f"🔄 *Story updated*\n{title}"
                + (f" by _{author}_" if author else "")
                + f"\n+{new_chapters} new chapter"
                + ("s" if new_chapters != 1 else "")
            )
        )
    
    def notify_story_deleted(self, title: str):
        self._fire_and_forget(
            self.send_message(
                f"🗑️ *Story deleted*\n{title}"
            )
        )