CREATE TABLE settings (
    user_id INTEGER PRIMARY KEY,
    theme TEXT DEFAULT 'light',
    font_size INTEGER DEFAULT 16,
    sort TEXT DEFAULT 'title'
);

INSERT OR IGNORE INTO settings (user_id) VALUES (1);