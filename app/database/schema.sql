-- =========================
-- BOOKS TABLE
-- =========================

CREATE TABLE IF NOT EXISTS books(

    id SERIAL PRIMARY KEY,

    work_key VARCHAR(50) UNIQUE,

    title TEXT NOT NULL,

    tags TEXT[],

    publish_date DATE,

    rating DOUBLE PRECISION
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

    password TEXT NOT NULL DEFAULT ''
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