# novelcast/services/page_service.py

from pathlib import Path


class PageService:
    def __init__(self, qm):
        self.qm = qm

    # ─────────────────────────────
    # Dashboard
    # ─────────────────────────────
    def get_dashboard(self, sort_key: str):
        subs_raw = self.qm.get_subscriptions()

        subs = []
        for s in subs_raw:
            title = s.get("title") or s.get("url") or ""

            subs.append({
                **s,
                "display_title": title,
                "thumbnail_letter": title[0].upper() if title else "N",
            })

        if sort_key == "last_chapter":
            subs.sort(key=lambda x: x.get("last_chapter", 0), reverse=True)
        elif sort_key == "url":
            subs.sort(key=lambda x: (x.get("url") or "").lower())
        else:
            subs.sort(key=lambda x: (x.get("display_title") or "").lower())

        return subs

    # ─────────────────────────────
    # Story page
    # ─────────────────────────────
    def get_story(self, url: str):
        sub = self.qm.get_subscription(url)

        if not sub or not sub.get("story_path"):
            return None, None

        story_path = Path(sub["story_path"])
        chapters = []

        if story_path.exists():
            chapters = sorted(story_path.glob("*.html"))

        return sub, [c.name for c in chapters]

    # ─────────────────────────────
    # Chapter page
    # ─────────────────────────────
    def get_chapter(self, url: str, chapter: str):
        sub = self.qm.get_subscription(url)

        if not sub or not sub.get("story_path"):
            return None, None, "Story not found"

        file_path = Path(sub["story_path"]) / chapter

        if not file_path.exists():
            return None, None, "Chapter not found"

        html = file_path.read_text(encoding="utf-8", errors="ignore")

        return sub, html, None