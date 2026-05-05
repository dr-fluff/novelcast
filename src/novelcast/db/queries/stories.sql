-- novelcast/db/queries/stories.sql

-- ========== STORIES ==========

-- name: list
SELECT * FROM stories
ORDER BY created_at DESC;

-- name: get_by_id
SELECT * FROM stories WHERE id = ?;

-- name: get_by_url
SELECT * FROM stories WHERE source_url = ?;

-- name: insert
INSERT INTO stories (title, author, source_url)
VALUES (?, ?, ?);

-- name: upsert_by_url
INSERT INTO stories (title, author, source_url)
VALUES (?, ?, ?)
ON CONFLICT(source_url) DO UPDATE SET
    title = excluded.title,
    author = excluded.author,
    last_updated = CURRENT_TIMESTAMP;

-- name: update_metadata
UPDATE stories
SET title = ?, author = ?, last_updated = CURRENT_TIMESTAMP
WHERE id = ?;

-- name: update_paths
UPDATE stories
SET local_path = ?, cover_path = ?
WHERE id = ?;

-- name: update_chapter_stats
UPDATE stories
SET total_chapters = ?,
    downloaded_chapters = ?,
    latest_downloaded_chapter = ?,
    latest_online_chapter = ?,
    online_chapters = ?
WHERE id = ?;

-- name: delete
DELETE FROM stories WHERE id = ?;

-- ========== CHAPTER CROSS QUERY (better moved later, but kept for now) ==========

-- name: get_chapter_file_paths
SELECT file_path
FROM chapters
WHERE story_id = ?
    AND COALESCE(file_path, '') != '';

-- name: get_chapter_numbers
SELECT chapter_number
FROM chapters
WHERE story_id = ?;

-- ========== CASCADE DELETES (optional but cleaner if DB doesn't enforce FK) ==========

-- name: delete_reading_progress
DELETE FROM reading_progress WHERE story_id = ?;

-- name: delete_permissions
DELETE FROM story_permissions WHERE story_id = ?;

-- name: delete_update_jobs
DELETE FROM update_jobs WHERE story_id = ?;

-- name: delete_chapters
DELETE FROM chapters WHERE story_id = ?;