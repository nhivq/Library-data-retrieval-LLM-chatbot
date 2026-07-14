CREATE TABLE authors(

    author_key TEXT PRIMARY KEY,

    author_name TEXT NOT NULL,

    fuller_name TEXT,

    alternate_names TEXT[],

    birth_date TEXT,

    death_date TEXT,

    bio TEXT,

    photo_id INTEGER,

    links JSONB,

    openlibrary_updated_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()

);


CREATE TABLE books(

    work_key TEXT PRIMARY KEY,

    title TEXT NOT NULL,

    description TEXT,

    tags TEXT[],

    languages TEXT[],

    publishers TEXT[],

    cover_id INTEGER,

    publish_date DATE,

    rating DOUBLE PRECISION,

    created_at TIMESTAMP DEFAULT NOW()

);


CREATE TABLE editions(

    edition_key TEXT PRIMARY KEY,

    work_key TEXT,

    isbn10 TEXT,

    isbn13 TEXT,

    publishers TEXT[],

    publish_date TEXT,

    pages INTEGER,

    languages TEXT[],

    cover_id INTEGER,

    created_at TIMESTAMP DEFAULT NOW(),

    FOREIGN KEY(work_key)
    REFERENCES books(work_key)

);


CREATE TABLE book_authors(

    work_key TEXT,

    author_key TEXT,

    PRIMARY KEY(work_key, author_key),

    FOREIGN KEY(work_key)
    REFERENCES books(work_key),

    FOREIGN KEY(author_key)
    REFERENCES authors(author_key)

);


CREATE INDEX idx_book_title
ON books(title);


CREATE INDEX idx_author_name
ON authors(author_name);


CREATE INDEX idx_book_tags
ON books
USING GIN(tags);
