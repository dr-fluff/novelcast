"""
anubis_shim.py - FlareSolverr-compatible HTTP endpoint that gets past Anubis.

Exposes POST /v1 with the same request/response shape FanFicFare expects from
FlareSolverr (request.get / request.post, sessions.* stubs), but drives a real
Chromium via Playwright and waits until the Anubis (or Cloudflare) interstitial
is gone before returning the HTML.

A persistent browser profile keeps the Anubis auth cookie between requests and
across restarts, so the proof-of-work only runs when the cookie has expired.

Setup (inside the NovelCast venv):
    pip install playwright
    playwright install chromium
    playwright install-deps chromium        # Debian/Ubuntu system libraries

Run:
    uvicorn anubis_shim:app --host 127.0.0.1 --port 8192

Env vars (all optional):
    SHIM_USER_DATA_DIR   browser profile dir          (default: ./anubis_profile)
    SHIM_HEADLESS        1 = headless, 0 = headed     (default: 1)
    SHIM_CONCURRENCY     parallel pages               (default: 2)
    SHIM_BLOCK_ASSETS    1 = skip images/media/fonts  (default: 1)
    SHIM_USER_AGENT      override the browser UA
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from playwright.async_api import BrowserContext, async_playwright

USER_DATA_DIR = os.environ.get("SHIM_USER_DATA_DIR", "./anubis_profile")
HEADLESS = os.environ.get("SHIM_HEADLESS", "1") != "0"
CONCURRENCY = int(os.environ.get("SHIM_CONCURRENCY", "2"))
BLOCK_ASSETS = os.environ.get("SHIM_BLOCK_ASSETS", "1") != "0"
USER_AGENT = os.environ.get(
    "SHIM_USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36",
)

# Lower-cased title fragments that mean "still on an interstitial".
CHALLENGE_TITLES = (
    "making sure you're not a bot",
    "just a moment",
    "checking your browser",
    "attention required",
)

log = logging.getLogger("anubis_shim")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    pw = await async_playwright().start()
    ctx: BrowserContext = await pw.chromium.launch_persistent_context(
        USER_DATA_DIR,
        headless=HEADLESS,
        user_agent=USER_AGENT,
        viewport={"width": 1280, "height": 800},
        args=[
            "--disable-blink-features=AutomationControlled",
            # Launch-flag UA also applies to web workers; Playwright's user_agent
            # option does not, and Anubis 403s the worker script as HeadlessChrome.
            f"--user-agent={USER_AGENT}",
        ],
    )
    if BLOCK_ASSETS:

        async def _route(route):
            if (
                route.request.resource_type in ("image", "media", "font")
                and "/.within.website/" not in route.request.url
            ):
                await route.abort()
            else:
                await route.continue_()

        await ctx.route("**/*", _route)

    _state["pw"] = pw
    _state["ctx"] = ctx
    _state["sem"] = asyncio.Semaphore(CONCURRENCY)
    log.info("Shim ready (headless=%s, concurrency=%s)", HEADLESS, CONCURRENCY)
    try:
        yield
    finally:
        await ctx.close()
        await pw.stop()


app = FastAPI(lifespan=lifespan)


def _envelope(status: str, message: str, start: float, solution: dict | None = None) -> dict:
    out = {
        "status": status,
        "message": message,
        "startTimestamp": int(start * 1000),
        "endTimestamp": int(time.time() * 1000),
        "version": "anubis-shim-1.0",
    }
    if solution is not None:
        out["solution"] = solution
    return out


async def _is_challenge(page) -> bool:
    try:
        title = (await page.title()).lower()
    except Exception:
        # Page is mid-navigation (Anubis reloads after solving); treat as pending.
        return True
    return any(t in title for t in CHALLENGE_TITLES)


async def _solution(page, ctx: BrowserContext, status: int, html: str) -> dict:
    return {
        "url": page.url,
        "status": status,
        "headers": {},
        "response": html,
        "cookies": await ctx.cookies(page.url),
        "userAgent": USER_AGENT,
    }


async def _do_get(url: str, timeout_ms: int) -> dict:
    ctx: BrowserContext = _state["ctx"]
    page = await ctx.new_page()
    last_status = {"value": 200}

    def _on_response(resp):
        try:
            if resp.request.resource_type == "document" and resp.frame == page.main_frame:
                last_status["value"] = resp.status
        except Exception:
            pass

    page.on("response", _on_response)
    deadline = time.monotonic() + timeout_ms / 1000
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

        while await _is_challenge(page):
            if time.monotonic() > deadline:
                raise TimeoutError("Interstitial still present at deadline")
            await asyncio.sleep(0.5)

        # Anubis redirects to the real page after solving; let that settle.
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10_000)
        except Exception:
            pass

        # Retry content() in case a navigation is still finishing.
        html = ""
        for _ in range(10):
            try:
                html = await page.content()
                break
            except Exception:
                await asyncio.sleep(0.3)

        # The challenge page itself returns 200; once cleared, that is the honest status
        # unless the real document reported something else.
        return await _solution(page, ctx, last_status["value"], html)
    finally:
        await page.close()


async def _do_post(url: str, post_data: str, timeout_ms: int) -> dict:
    ctx: BrowserContext = _state["ctx"]
    resp = await ctx.request.post(
        url,
        data=post_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=timeout_ms,
    )
    html = await resp.text()
    return {
        "url": resp.url,
        "status": resp.status,
        "headers": dict(resp.headers),
        "response": html,c
        "cookies": await ctx.cookies(url),
        "userAgent": USER_AGENT,
    }


@app.post("/v1")
async def v1(body: dict):
    start = time.time()
    cmd = body.get("cmd", "")

    if cmd == "sessions.create":
        out = _envelope("ok", "Session created (no-op)", start)
        out["session"] = body.get("session") or "shim-session"
        return out
    if cmd == "sessions.destroy":
        return _envelope("ok", "The session has been removed.", start)
    if cmd == "sessions.list":
        out = _envelope("ok", "", start)
        out["sessions"] = []
        return out

    if cmd not in ("request.get", "request.post"):
        return _envelope("error", f"Unsupported cmd: {cmd}", start)

    url = body.get("url")
    if not url:
        return _envelope("error", "Missing url", start)
    timeout_ms = int(body.get("maxTimeout", 60000))

    async with _state["sem"]:
        try:
            if cmd == "request.get":
                sol = await _do_get(url, timeout_ms)
            else:
                sol = await _do_post(url, body.get("postData", ""), timeout_ms)
        except Exception as e:
            log.exception("Request failed: %s", url)
            return _envelope("error", f"{type(e).__name__}: {e}", start)

    log.info("%s %s -> %s", cmd, url, sol["status"])
    return _envelope("ok", "Challenge solved or not present", start, sol)


@app.get("/")
async def index():
    return {"msg": "anubis-shim ready", "version": "anubis-shim-1.0"}