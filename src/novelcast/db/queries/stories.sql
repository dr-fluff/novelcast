-- name: list
SELECT * FROM stories;

-- name: get_by_id
SELECT * FROM stories WHERE id = ?;

-- name: get_by_url
SELECT * FROM stories WHERE source_url = ?;

-- name: delete
DELETE FROM stories WHERE id = ?;

-- name: upsert_story
INSERT INTO stories (title, author, source_url)
VALUES (?, ?, ?)
ON CONFLICT(source_url) DO UPDATE SET
    title = excluded.title,
    author = excluded.author,
    last_updated = CURRENT_TIMESTAMP;