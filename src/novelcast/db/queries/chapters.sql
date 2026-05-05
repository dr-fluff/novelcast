-- novelcast/db/queries/chapters.sql

-- name: insert
INSERT INTO chapters (
    story_id, chapter_number, title, url, file_path, is_downloaded
) VALUES (?, ?, ?, ?, ?, ?);

-- name: upsert_by_url
INSERT INTO chapters (
    story_id, chapter_number, title, url, file_path, is_downloaded
) VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(url) DO UPDATE SET
    story_id = excluded.story_id,
    chapter_number = excluded.chapter_number,
    title = excluded.title,
    file_path = excluded.file_path,
    is_downloaded = excluded.is_downloaded;

-- name: mark_downloaded_by_number
UPDATE chapters
SET is_downloaded = 1,
    file_path = ?
WHERE story_id = ? AND chapter_number = ?;

-- name: get_by_story
SELECT * FROM chapters
WHERE story_id = ?
ORDER BY chapter_number;

-- name: get_downloaded_by_story
SELECT * FROM chapters
WHERE story_id = ? AND is_downloaded = 1
ORDER BY chapter_number;

-- name: get_ids_downloaded_by_story
SELECT id FROM chapters
WHERE story_id = ? AND is_downloaded = 1
ORDER BY chapter_number;

-- name: get_numbers_by_story
SELECT chapter_number FROM chapters
WHERE story_id = ?;

-- name: get_by_number
SELECT * FROM chapters
WHERE story_id = ? AND chapter_number = ?;

-- name: get_by_id
SELECT * FROM chapters
WHERE id = ?;