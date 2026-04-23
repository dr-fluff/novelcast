-- name: get_story_permissions
SELECT * FROM story_permissions WHERE story_id = ?;

-- name: set_permission
INSERT OR REPLACE INTO story_permissions (
    story_id, group_id, can_read, can_download, can_delete
) VALUES (?, ?, ?, ?, ?);