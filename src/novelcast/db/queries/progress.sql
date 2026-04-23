-- name: get_progress
SELECT * FROM reading_progress
WHERE user_id = ? AND story_id = ?;

-- name: set_progress
INSERT OR REPLACE INTO reading_progress (
    user_id, story_id, last_chapter_id, last_position, updated_at
) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP);