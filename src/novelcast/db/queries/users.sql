-- name: create_user
INSERT INTO users (username, password_hash, role)
VALUES (?, ?, ?);

-- name: get_by_username
SELECT * FROM users
WHERE username = ?;

-- name: get_by_id
SELECT * FROM users
WHERE id = ?;

-- name: update_role
UPDATE users
SET role = ?
WHERE id = ?;