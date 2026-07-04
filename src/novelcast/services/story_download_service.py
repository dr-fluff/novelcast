# novelcast/services/story_download_service.py

import json
import logging
import re
import uuid
from pathlib import Path

from novelcast.utils.html import clean_html_description
from novelcast.utils.url_normalizer import normalize_story_url

logger = logging.getLogger(__name__)


class StoryDownloadService:
    def __init__(self, orchestrator, pipeline, parser, stories_repo, notifier=None):
        self.orchestrator  = orchestrator
        self.pipeline      = pipeline
        self.parser        = parser
        self.stories_repo  = stories_repo
        self.notifier      = notifier

    def _download_raw(self, url: str, progress_callback=None) -> dict:
        return self.orchestrator.download(url, progress_callback=progress_callback)

    def _parse_raw(self, raw: dict) -> dict:
        parsed = self.parser.parse(raw)
        parsed["source_url"] = raw.get("url") or raw.get("source_url")
        parsed["source_file_path"] = raw.get("file_path")
        return parsed

    def _filter_chapters(self, parsed: dict, selected_chapters: list[int]) -> dict:
        """Filter parsed chapters to only include selected chapter numbers."""
        if not selected_chapters:
            return parsed
        
        selected_set = set(selected_chapters)
        original_chapters = parsed.get("chapters", [])
        
        filtered = [ch for ch in original_chapters if ch.get("number") in selected_set]
        logger.debug(
            "Filtered chapters from %d to %d",
            len(original_chapters),
            len(filtered),
        )
        
        parsed["chapters"] = filtered
        return parsed

    def _persist_story(self, story_id: int, raw: dict, parsed: dict) -> list[int]:
        self._update_story_metadata(story_id, raw, parsed)

        if raw.get("file_path"):
            self.pipeline.persist(story_id, parsed)
        else:
            return self.pipeline.append_new_chapters(story_id, parsed)

        return [ch["number"] for ch in parsed.get("chapters", [])]

    def add_story(self, url: str, selected_chapters: list[int] | None = None):
        logger.debug("Story download requested of URL: %s", url)
        if selected_chapters:
            logger.debug("Filtering to selected chapters: %s", selected_chapters)

        normalized_url = normalize_story_url(url)
        download_id    = str(uuid.uuid4())
        self._emit("download_started", {"download_id": download_id, "source_url": normalized_url})

        try:
            existing = self.stories_repo.get_by_url(normalized_url)
            if existing:
                self._emit("download_finished", {
                    "download_id": download_id,
                    "story_id":   existing["id"],
                    "title":      existing.get("title"),
                })
                return existing["id"]

            def progress(message: str, progress_value: int | None = None):
                self._emit("download_progress", {
                    "download_id": download_id,
                    "source_url":  normalized_url,
                    "progress":    progress_value,
                    "indeterminate": progress_value is None,
                })

            raw        = self._download_raw(normalized_url, progress_callback=progress)
            source_url = raw.get("url") or normalized_url

            story_id = self.stories_repo.create(
                raw.get("title") or "Unknown",
                raw.get("author"),
                source_url,
            )

            parsed = self._parse_raw(raw)

            if selected_chapters:
                parsed = self._filter_chapters(parsed, selected_chapters)

            self._update_story_metadata(story_id, raw, parsed)

            author_name = parsed.get("author") or raw.get("author")
            if author_name:
                from novelcast.db.repositories.author_repository import AuthorRepository
                author_repo = AuthorRepository(self.stories_repo._session_factory)
                author_id   = author_repo.get_or_create(author_name)
                author_repo.link_to_story(author_id, story_id)

            self.pipeline.persist(story_id, parsed)
            self._refresh_metadata_from_json(story_id)
            
            # ── Telegram ──────────────────────────────────
            telegram = getattr(self, "telegram", None)
            if telegram:
                try:
                    telegram.notify_story_added(
                        title=parsed.get("title") or raw.get("title") or "Unknown",
                        author=parsed.get("author") or raw.get("author"),
                        link=parsed.get("source_url") or raw.get("url") or normalized_url,
                    )
                except Exception:
                    logger.exception(
                        "Failed to send telegram notification"
                    )

            # Verify all chapter files landed on disk
            check = self.pipeline.integrity_check(story_id)
            if not check["ok"]:
                self._handle_integrity_failure(story_id, normalized_url, check, download_id)

            self._emit("download_finished", {
                "download_id": download_id,
                "story_id":    story_id,
                "title":       parsed.get("title"),
            })

            return story_id

        except Exception as e:
            self._emit("download_failed", {
                "download_id": download_id,
                "source_url":  normalized_url,
                "error":       str(e),
            })
            raise

    def update_story(self, story: dict) -> dict:
        story_id = story.get("id")
        source_url = story.get("source_url")
        title = story.get("title")
        if not story_id or not source_url:
            return {"story_id": story_id, "new_chapters": 0, "skipped": True}

        logger.info("Updating story", extra={"story_name": title, "story_id": story_id, "source_url": source_url})
        self._emit("update_story_started", {
            "story_id": story_id,
            "title": title,
            "source_url": source_url,
        })

        raw = self._download_raw(source_url)
        parsed = self._parse_raw(raw)
        self._update_story_metadata(story_id, raw, parsed)

        existing_numbers = self.pipeline.chapters_repo.get_chapter_numbers(story_id)
        parsed_numbers = [ch["number"] for ch in parsed.get("chapters", [])]
        new_chapters = [number for number in parsed_numbers if number not in existing_numbers]

        if raw.get("file_path"):
            self.pipeline.persist(story_id, parsed)
        else:
            new_chapters = self.pipeline.append_new_chapters(story_id, parsed)

        self._refresh_metadata_from_json(story_id)

        # Always integrity-check after update — catches missing files even
        # when no new chapters were downloaded (no EPUB → no parser run).
        check = self.pipeline.integrity_check(story_id)
        if not check["ok"]:
            self._handle_integrity_failure(story_id, source_url, check, download_id=None)

        final_title = parsed.get("title") or title

        if new_chapters:
            self._emit("update_progress", {
                "story_id": story_id,
                "title": final_title,
                "new_chapters": len(new_chapters),
            })
            self._emit("sync_story_updated", {
                "story_id": story_id,
                "title": final_title,
                "new_chapters": len(new_chapters),
            })
            
            # ── Telegram ──────────────────────────────
            telegram = getattr(self, "telegram", None)
            if telegram:
                logger.info("telegram msg notify_story_updated")
                try:
                    telegram.notify_story_updated(
                        title=final_title,
                        author=parsed.get("author"),
                        link=source_url,
                        new_chapters=len(new_chapters),
                    )
                except Exception:
                    logger.exception(
                        "Failed to send telegram notification"
                    )

        self._emit("update_finished", {
            "story_id": story_id,
            "title": final_title,
            "new_chapters": len(new_chapters),
        })

        return {
            "story_id": story_id,
            "new_chapters": len(new_chapters),
            "chapter_numbers": new_chapters,
        }

    def _handle_integrity_failure(self, story_id: int, source_url: str, check: dict, download_id: str | None) -> None:
        """
        Called when integrity_check reports missing files after persist/update.

        - Logs the outcome.
        - Emits events so the frontend can show a warning.
        - If needs_redownload=True, triggers a fresh download.
        """
        restored   = check.get("restored", [])
        not_in_epub = check.get("not_in_epub", [])
        needs_redownload = check.get("needs_redownload", False)

        if restored:
            logger.info(
                "integrity_check: story %s restored %d chapter(s) from local EPUB: %s",
                story_id, len(restored), restored,
            )

        if not_in_epub:
            logger.warning(
                "integrity_check: story %s has %d chapter(s) missing from both disk and EPUB "
                "(likely removed from site): %s",
                story_id, len(not_in_epub), not_in_epub,
            )
            self._emit("integrity_warning", {
                "story_id":    story_id,
                "source_url":  source_url,
                "not_in_epub": not_in_epub,
                "message":     f"{len(not_in_epub)} chapter(s) could not be restored — may have been removed from the site.",
            })

        if needs_redownload:
            logger.warning(
                "integrity_check: story %s has missing files and no local EPUB — triggering redownload",
                story_id,
            )
            self._emit("integrity_redownload", {
                "story_id":   story_id,
                "source_url": source_url,
                "message":    "Missing chapter files detected. Re-downloading from source.",
            })
            try:
                raw    = self._download_raw(source_url)
                parsed = self._parse_raw(raw)
                self._update_story_metadata(story_id, raw, parsed)
                self.pipeline.persist(story_id, parsed)
                self._refresh_metadata_from_json(story_id)
                logger.info("integrity_check: redownload complete for story %s", story_id)
            except Exception:
                logger.exception("integrity_check: redownload failed for story %s", story_id)

    def sync_story(self, story: dict) -> dict:
        return self.update_story(story)

    def check_story_updates(self, story: dict) -> dict:
        story_id = story.get("id")
        source_url = story.get("source_url")
        if not story_id or not source_url:
            return {"story_id": story_id, "pending_chapters": 0, "chapter_numbers": [], "skipped": True}

        raw = self.orchestrator.check_updates(source_url)
        online_numbers = self._online_chapter_numbers(raw)
        local_numbers = self.pipeline.chapters_repo.get_chapter_numbers(story_id)
        pending = sorted(number for number in online_numbers if number not in local_numbers)

        return {
            "story_id": story_id,
            "title": raw.get("title") or story.get("title"),
            "pending_chapters": len(pending),
            "chapter_numbers": pending,
            "online_chapters": len(online_numbers),
            "local_chapters": len(local_numbers),
        }

    def _online_chapter_numbers(self, raw: dict) -> list[int]:
        chapters = raw.get("chapters") or raw.get("raw", {}).get("chapters")
        chapters = chapters or raw.get("zchapters") or raw.get("raw", {}).get("zchapters")

        if chapters:
            return list(range(1, len(chapters) + 1))

        for key in ("numChapters", "num_chapters", "chapter_count"):
            value = raw.get(key) or raw.get("raw", {}).get(key)
            try:
                count = int(value)
            except (TypeError, ValueError):
                continue
            return list(range(1, count + 1))

        return []

    def _update_story_metadata(self, story_id: int, raw: dict, parsed: dict) -> None:
        metadata_json = self._load_local_metadata_json(story_id)
        metadata = self._extract_metadata(metadata_json or raw)
        if metadata is not None:
            self.stories_repo.update_full_metadata(
                story_id=story_id,
                title=metadata.get("title") or parsed.get("title") or raw.get("title") or "Unknown",
                author=metadata.get("author") or parsed.get("author") or raw.get("author"),
                subtitle=metadata.get("subtitle"),
                description=metadata.get("description"),
                publish_year=metadata.get("publish_year"),
                language=metadata.get("language"),
                series=metadata.get("series"),
                genres=metadata.get("genres"),
                tags=metadata.get("tags"),
                source_url=parsed.get("source_url"),
                story_site_id=raw.get("story_site_id"),
            )
            return

        self.stories_repo.update_metadata(
            story_id,
            parsed.get("title") or raw.get("title") or "Unknown",
            parsed.get("author") or raw.get("author"),
        )

    def _load_local_metadata_json(self, story_id: int) -> dict | None:
        story = self.stories_repo.get_by_id(story_id)
        if not story:
            return None

        local_path = story.get("local_path")
        if not local_path:
            return None

        metadata_path = Path(local_path) / "metadata.json"
        if not metadata_path.exists():
            return None

        try:
            return json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Failed to read metadata.json for story %s", story_id)
            return None

    def _refresh_metadata_from_json(self, story_id: int) -> None:
        metadata = self._load_local_metadata_json(story_id)
        if not metadata:
            return

        story = self.stories_repo.get_by_id(story_id)
        if not story:
            return

        parsed = {"source_url": story.get("source_url")}
        self._update_story_metadata(story_id, metadata, parsed)

    def _extract_metadata(self, raw: dict) -> dict:
        if not raw:
            return None

        title = raw.get("title")
        author = raw.get("author")

        subtitle = raw.get("subtitle") or raw.get("subtitleText")

        description = raw.get("description") or raw.get("summary")
        if isinstance(description, str):
            description = clean_html_description(description)

        publish_year = self._parse_publish_year(
            raw.get("datePublished") or raw.get("published") or raw.get("year")
        )

        language = raw.get("language") or raw.get("langcode")

        series = self._normalize_metadata_list(
            raw.get("series") or raw.get("series_name") or raw.get("series_info")
        )

        genres = self._normalize_metadata_list(
            raw.get("genre") or raw.get("genres")
        )

        tags = self._normalize_metadata_list(
            raw.get("subject_tags") or raw.get("tags") or raw.get("subjects")
        )

        metadata = {
            "title": title,
            "author": author,
            "subtitle": subtitle,
            "description": description,
            "publish_year": publish_year,
            "language": language,
            "series": series,
            "genres": genres,
            "tags": tags,
        }

        # only hard-fail if completely useless
        if not title and not author and not description:
            return None

        return metadata

    def _parse_publish_year(self, value):
        if value is None:
            return None

        if isinstance(value, int):
            return value

        raw_value = str(value).strip()
        if not raw_value:
            return None

        import re
        match = re.search(r"(\d{4})", raw_value)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None

        try:
            return int(raw_value)
        except ValueError:
            return None

    def _normalize_metadata_list(self, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in re.split(r"[;,]", value) if item.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()] if str(value).strip() else []

    def _emit(self, event_type: str, payload: dict):
        if self.notifier:
            try:
                self.notifier(event_type, payload)
            except Exception:
                logger.exception("Notifier failed for %s", event_type)
    
    def temp_dir(self):
        self.temp_dir_path = "temp"