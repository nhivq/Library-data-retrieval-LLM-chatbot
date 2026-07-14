-- =========================
-- BOOKS TABLE
-- =========================

CREATE TABLE IF NOT EXISTS books(

    id SERIAL PRIMARY KEY,

    -- OpenLibrary work identifier, for example /works/OL123W.
    work_key VARCHAR(50) UNIQUE,

    title TEXT NOT NULL,

    description TEXT,

    -- Arrays preserve the imported metadata without requiring lookup tables.
    tags TEXT[],

    languages TEXT[],

    publishers TEXT[],

    cover_id INTEGER,

    publish_date DATE,

    rating DOUBLE PRECISION,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- =========================
-- AUTHORS TABLE
-- =========================

CREATE TABLE IF NOT EXISTS authors(

    author_key VARCHAR(50) PRIMARY KEY,

    author_name TEXT NOT NULL
);



-- =========================
-- USERS TABLE
-- =========================

CREATE TABLE IF NOT EXISTS users(

    user_id SERIAL PRIMARY KEY,

    username TEXT NOT NULL,

    email TEXT UNIQUE NOT NULL,

    password TEXT NOT NULL DEFAULT '',

    oauth_provider TEXT,

    oauth_id TEXT,

    role TEXT NOT NULL DEFAULT 'user',

    UNIQUE(oauth_provider, oauth_id)
);



-- =========================
-- BOOK AUTHORS TABLE
-- =========================

CREATE TABLE IF NOT EXISTS book_authors(

    work_key VARCHAR(50) NOT NULL,

    author_key VARCHAR(50) NOT NULL,

    PRIMARY KEY(work_key, author_key),

    FOREIGN KEY(work_key)
    REFERENCES books(work_key),

    FOREIGN KEY(author_key)
    REFERENCES authors(author_key)
);



-- =========================
-- CONVERSATIONS TABLE
-- =========================
CREATE TABLE conversations (

    id SERIAL PRIMARY KEY,

    -- Frontend-generated session id used to group chat messages.
    session_id VARCHAR(255) UNIQUE NOT NULL,

    user_id INTEGER
        REFERENCES users(user_id)
        ON DELETE CASCADE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- =========================
-- MESSAGES TABLE
-- =========================
CREATE TABLE messages (
    
    id SERIAL PRIMARY KEY,

    conversation_id INTEGER NOT NULL
        REFERENCES conversations(id)
        ON DELETE CASCADE,

    -- Matches OpenAI-style chat roles: system, user, assistant, tool.
    role VARCHAR(50) NOT NULL,

    content TEXT NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- =========================
-- BOOKMARKS TABLE
-- =========================

CREATE TABLE IF NOT EXISTS bookmarks(

    user_id INTEGER NOT NULL,

    work_key VARCHAR(50) NOT NULL,

    -- One user can save a book only once.
    PRIMARY KEY(user_id, work_key),

    FOREIGN KEY(user_id)
    REFERENCES users(user_id),

    FOREIGN KEY(work_key)
    REFERENCES books(work_key)
);



-- =========================
-- INDEXES
-- =========================

CREATE INDEX IF NOT EXISTS idx_title
ON books(title);

CREATE INDEX IF NOT EXISTS idx_rating
ON books(rating);

CREATE INDEX IF NOT EXISTS idx_publish_date
ON books(publish_date);

CREATE INDEX IF NOT EXISTS idx_author_name
ON authors(author_name);
