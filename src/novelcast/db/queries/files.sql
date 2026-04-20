-- name: add_file
INSERT INTO files (author, story, filename, path, size, last_updated)
VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP);

-- name: get_by_id
SELECT * FROM files
WHERE id = ?;

-- name: list_by_story
SELECT * FROM files
WHERE author = ? AND story = ?;

-- name: update_metadata
UPDATE files
SET size = ?, last_updated = CURRENT_TIMESTAMP
WHERE id = ?;

-- Delete file
DELETE FROM files
WHERE id = ?;

-- Get groups allowed for file
SELECT group_id FROM file_permissions
WHERE file_id = ?;

-- Grant access
INSERT INTO file_permissions (file_id, group_id)
VALUES (?, ?);

-- Revoke access
DELETE FROM file_permissions
WHERE file_id = ? AND group_id = ?;

-- Get user progress
SELECT * FROM user_file_progress
WHERE user_id = ? AND file_id = ?;

-- Update progress
INSERT INTO user_file_progress (user_id, file_id, last_read_position, last_read_at)
VALUES (?, ?, ?, CURRENT_TIMESTAMP)
ON CONFLICT(user_id, file_id)
DO UPDATE SET
    last_read_position = excluded.last_read_position,
    last_read_at = excluded.last_read_at;