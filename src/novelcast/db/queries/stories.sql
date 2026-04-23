-- name: list
SELECT * FROM stories;

-- name: get_by_id
SELECT * FROM stories WHERE id = ?;

-- name: get_by_url
SELECT * FROM stories WHERE source_url = ?;

-- name: create
INSERT INTO stories (title, author, source_url)
VALUES (?, ?, ?);

-- name: delete
DELETE FROM stories WHERE id = ?;