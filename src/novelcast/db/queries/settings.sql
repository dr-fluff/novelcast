-- name: get_user_settings
SELECT * FROM user_settings WHERE user_id = ?;

-- name: set_theme
UPDATE user_settings
SET theme = ?
WHERE user_id = ?;

-- name: set_server_setting
INSERT OR REPLACE INTO server_settings (key, value)
VALUES (?, ?);

-- name: get_server_setting
SELECT value FROM server_settings WHERE key = ?;