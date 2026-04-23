-- name: get_by_story
SELECT * FROM chapters WHERE story_id = ? ORDER BY chapter_number;

-- name: insert
INSERT INTO chapters (
    story_id, chapter_number, title, url, file_path, is_downloaded
) VALUES (?, ?, ?, ?, ?, ?);

-- name: mark_downloaded
UPDATE chapters
SET is_downloaded = 1, file_path = ?
WHERE id = ?;