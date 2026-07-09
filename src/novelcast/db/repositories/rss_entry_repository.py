# novelcast/db/repositories/rss_entry_repository.py
from sqlalchemy import select

from novelcast.db.repositories.base import BaseRepository
from novelcast.db.models import RssEntry


class RssEntryRepository(BaseRepository):

    def exists(self, source: str, guid: str) -> bool:
        with self.session_no_commit() as db:
            return (
                db.scalars(
                    select(RssEntry)
                    .where(
                        RssEntry.source == source,
                        RssEntry.guid == guid,
                    )
                )
                .first()
                is not None
            )

    def create(self, entry: dict) -> dict:
        with self.session() as db:
            rss = RssEntry(
                source=entry["source"],
                guid=entry["guid"],
                title=entry.get("title"),
                link=entry.get("link"),
                published=entry.get("published"),
            )

            db.add(rss)
            db.flush()  # populate rss.id before the row is committed/detached

            return {"id": rss.id}

    def mark_processed(self, entry_id: int) -> None:
        with self.session() as db:
            row = db.get(RssEntry, entry_id)
            if row:
                row.processed = True