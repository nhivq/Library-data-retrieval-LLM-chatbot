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