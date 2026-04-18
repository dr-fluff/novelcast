CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE,
    title TEXT,
    last_chapter INTEGER DEFAULT 0,
    requested_chapters INTEGER DEFAULT 0,
    downloaded_chapters INTEGER DEFAULT 0,
    available_chapters INTEGER DEFAULT 0,
    cover_url TEXT,
    story_path TEXT
);