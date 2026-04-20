-- name: get_user_settings
SELECT * FROM user_settings
WHERE user_id = ?;

-- name: set_theme
UPDATE user_settings
SET theme = ?
WHERE user_id = ?;

-- name: set_server_setting
INSERT INTO server_settings (key, value)
VALUES (?, ?)
ON CONFLICT(key)
DO UPDATE SET value = excluded.value;

-- Create default settings
INSERT INTO user_settings (user_id, theme, auto_update, font_size)
VALUES (?, 'light', 1, 14);

-- Update theme
UPDATE user_settings
SET theme = ?
WHERE user_id = ?;

-- Update auto update
UPDATE user_settings
SET auto_update = ?
WHERE user_id = ?;

-- Update font size
UPDATE user_settings
SET font_size = ?
WHERE user_id = ?;

-- Get all server settings
SELECT * FROM server_settings;

-- Get one setting
SELECT value FROM server_settings
WHERE key = ?;

-- Set / update setting
INSERT INTO server_settings (key, value)
VALUES (?, ?)
ON CONFLICT(key)
DO UPDATE SET value = excluded.value;

-- Delete setting (admin only)
DELETE FROM server_settings
WHERE key = ?;