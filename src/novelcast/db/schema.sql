-- USERS
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_root INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- GROUPS / ROLES
CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS user_groups (
    user_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, group_id)
);

-- STORIES (LIBRARY CORE)
CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author TEXT,
    title TEXT NOT NULL,
    source_url TEXT UNIQUE,

    total_chapters INTEGER DEFAULT 0,
    downloaded_chapters INTEGER DEFAULT 0,

    latest_online_chapter INTEGER,
    latest_downloaded_chapter INTEGER,

    local_path TEXT UNIQUE,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT
);

-- CHAPTERS
CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER NOT NULL,

    chapter_number INTEGER,
    title TEXT,
    url TEXT,

    is_downloaded INTEGER DEFAULT 0,
    file_path TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- PERMISSIONS
CREATE TABLE IF NOT EXISTS story_permissions (
    story_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,

    can_read INTEGER DEFAULT 1,
    can_download INTEGER DEFAULT 0,
    can_delete INTEGER DEFAULT 0,

    PRIMARY KEY (story_id, group_id)
);

-- READING PROGRESS
CREATE TABLE IF NOT EXISTS reading_progress (
    user_id INTEGER NOT NULL,
    story_id INTEGER NOT NULL,

    last_chapter_id INTEGER,
    last_position INTEGER DEFAULT 0,

    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (user_id, story_id)
);

-- USER SETTINGS
CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER PRIMARY KEY,
    theme TEXT DEFAULT 'light',
    font_size INTEGER DEFAULT 14,
    line_height REAL DEFAULT 1.5,
    auto_update INTEGER DEFAULT 1
);

-- SERVER SETTINGS
CREATE TABLE IF NOT EXISTS server_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- UPDATE JOBS
CREATE TABLE IF NOT EXISTS update_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER,
    status TEXT DEFAULT 'pending',
    last_run TEXT,
    next_run TEXT,
    error TEXT
);