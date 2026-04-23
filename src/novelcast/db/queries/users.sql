-- name: get_by_id
SELECT * FROM users WHERE id = ?;

-- name: get_by_username
SELECT * FROM users WHERE username = ?;

-- name: create
INSERT INTO users (username, password_hash, is_root)
VALUES (?, ?, ?);

-- name: list
SELECT * FROM users;

-- name: delete
DELETE FROM users WHERE id = ?;