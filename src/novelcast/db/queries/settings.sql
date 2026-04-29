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

-- name: get_all
SELECT * FROM server_settings ORDER BY key;

-- name: upsert_user_settings
INSERT INTO user_settings (user_id, theme, font_size, line_height, auto_update)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(user_id) DO UPDATE SET
    theme = excluded.theme,
    font_size = excluded.font_size,
    line_height = excluded.line_height,
    auto_update = excluded.auto_update;
