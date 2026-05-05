-- novelcast/db/queries/users.sql

-- name: get_by_id
SELECT * FROM users WHERE id = ?;

-- name: get_by_username
SELECT * FROM users WHERE username = ?;

-- name: list
SELECT * FROM users;

-- name: count
SELECT COUNT(*) as total FROM users;

-- name: create
INSERT INTO users (username, password_hash, is_root)
VALUES (?, ?, ?);

-- name: set_root
UPDATE users SET is_root = 1 WHERE id = ?;

-- name: delete
DELETE FROM users WHERE id = ?;