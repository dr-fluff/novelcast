# novelcast/services/telegram_service.py
# Full replacement — changes marked with # ← CHANGED

import asyncio
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
_MAX_BACKOFF  = 30
_MAX_FAILURES = 5
_OFFLINE_RETRY_INTERVAL = 60 


class TelegramService:

    def __init__(self, settings_service, story_service, download_service):
        self.settings  = settings_service
        self.stories   = story_service
        self.downloads = download_service

        self._task:   Optional[asyncio.Task] = None
        self._loop:   Optional[asyncio.AbstractEventLoop] = None
        self._offset  = 0

        self._disabled             = False   # permanent auth failure
        self._consecutive_failures = 0

    # ── settings helpers ──────────────────────────────────────────────────

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

    # ── lifecycle ─────────────────────────────────────────────────────────

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
            logger.info("Telegram polling started (chat_id=%s)", self._chat_id())
        except RuntimeError:
            logger.exception("Failed to start Telegram service: no running event loop")

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
        if self._disabled:
            logger.warning("Telegram is permanently disabled; restart blocked")
            return
        self.stop()
        self._consecutive_failures = 0
        self.start()

    # ── poll loop ─────────────────────────────────────────────────────────

    async def _poll_loop(self):
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0,   # ← CHANGED: was 10s; fail fast when offline
                read=35.0,     # long-poll read must exceed Telegram's timeout param
                write=5.0,     # ← CHANGED: was 10s
                pool=5.0,      # ← CHANGED: was 10s
            )
        ) as client:
            while True:
                try:
                    await self._poll_once(client)
                    # successful poll — reset failure counter
                    if self._consecutive_failures > 0:
                        logger.info("Telegram reconnected after %d failures", self._consecutive_failures)
                    self._consecutive_failures = 0

                except asyncio.CancelledError:
                    logger.info("Telegram polling cancelled")
                    break

                except Exception:
                    self._consecutive_failures += 1

                    if self._consecutive_failures < _MAX_FAILURES:
                        # Normal transient error — short backoff, keep logging
                        backoff = min(_MAX_BACKOFF, 2 ** self._consecutive_failures)
                        logger.warning(          # ← CHANGED: was logger.exception (huge traceback every time)
                            "Telegram poll failed (%d/%d), retrying in %ds",
                            self._consecutive_failures,
                            _MAX_FAILURES,
                            backoff,
                        )
                        await asyncio.sleep(backoff)

                    else:
                        # ← CHANGED: was `self._disabled = True; break`
                        # Don't die permanently — just go quiet and retry slowly.
                        # This way Telegram recovers automatically when internet returns.
                        if self._consecutive_failures == _MAX_FAILURES:
                            logger.warning(
                                "Telegram appears offline after %d failures. "
                                "Will retry every %ds silently.",
                                _MAX_FAILURES,
                                _OFFLINE_RETRY_INTERVAL,
                            )
                        await asyncio.sleep(_OFFLINE_RETRY_INTERVAL)

    async def _poll_once(self, client: httpx.AsyncClient):
        if not self._enabled():
            await asyncio.sleep(5)   # ← CHANGED: avoid tight spin if disabled mid-run
            return

        r = await client.get(
            self._url("getUpdates"),
            params={
                "offset":          self._offset,
                "timeout":         30,           # Telegram long-poll seconds
                "allowed_updates": ["message"],
            },
        )

        if r.status_code in (401, 403):
            logger.error("Telegram auth failed (%s). Disabling bot permanently.", r.status_code)
            self._disabled = True   # only permanent-disable on auth failure, not network errors
            return

        data = r.json()
        if not data.get("ok"):
            logger.warning("Telegram API error: %s", data)
            return

        for update in data["result"]:
            self._offset = update["update_id"] + 1
            await self._handle_update(update)

    # ── rest of the class unchanged ───────────────────────────────────────

    def _handle_task_result(self, task: asyncio.Task):
        try:
            task.result()
        except asyncio.CancelledError:
            logger.debug("Telegram background task cancelled")
        except Exception:
            logger.exception("Telegram background task failed")

    def _fire_and_forget(self, coro):
        if self._disabled:
            logger.debug("Telegram notification skipped: service disabled")
            return
        if self._loop is None:
            logger.warning("Telegram notification skipped: no event loop")
            return
        if self._loop.is_closed():
            logger.warning("Telegram notification skipped: event loop closed")
            return
        try:
            task = self._loop.create_task(coro)
            task.add_done_callback(self._handle_task_result)
        except Exception:
            logger.exception("Failed to schedule Telegram notification")

    async def _handle_update(self, update: dict):
        msg     = update.get("message", {})
        text    = msg.get("text", "").strip()
        chat_id = str(msg.get("chat", {}).get("id", ""))

        if chat_id != self._chat_id():
            return

        if text.startswith("/status"):
            await self.send_message("✅ NovelCast is running.")
        elif text.startswith("/stories"):
            stories = await self.stories.list_stories(limit=10)
            lines   = [f"📚 {s.title} — {s.chapter_count}" for s in stories]
            await self.send_message("\n".join(lines) or "No stories")
        else:
            await self.send_message("Commands: /status /stories /download <url>")

    async def send_message(self, text: str):
        logger.info("Telegram message: %s", text)
        if not self._enabled():
            logger.debug("Skipping telegram send: service disabled")
            return
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    self._url("sendMessage"),
                    json={
                        "chat_id":    self._chat_id(),
                        "text":       text,
                        "parse_mode": "Markdown",
                    },
                )
            if r.status_code in (401, 403):
                logger.error("Telegram auth failed (%s). Disabling.", r.status_code)
                self._disabled = True
                return
            r.raise_for_status()
            if not r.json().get("ok"):
                logger.warning("Telegram API rejected message: %s", r.json())
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
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
                # ← CHANGED: connect was 10s; test should fail fast
            ) as client:
                r = await client.post(
                    self._url("sendMessage"),
                    json={"chat_id": self._chat_id(), "text": "👋 Telegram integration OK"},
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

    # ── notifications ─────────────────────────────────────────────────────

    def notify_story_added(self, title: str, author: str | None):
        self._fire_and_forget(
            self.send_message(
                f"📖 *New story added*\n{title}" + (f" by _{author}_" if author else "")
            )
        )

    def notify_story_updated(self, title: str, author: str | None, new_chapters: int):
        self._fire_and_forget(
            self.send_message(
                f"🔄 *Story updated*\n{title}"
                + (f" by _{author}_" if author else "")
                + f"\n+{new_chapters} new chapter" + ("s" if new_chapters != 1 else "")
            )
        )

    def notify_story_deleted(self, title: str):
        self._fire_and_forget(
            self.send_message(f"🗑️ *Story deleted*\n{title}")
        )