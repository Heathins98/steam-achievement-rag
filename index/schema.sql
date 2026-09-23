CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE achievements (
    api_name      TEXT PRIMARY KEY,
    display_name  TEXT NOT NULL,
    description   TEXT,
    is_hidden     BOOLEAN NOT NULL,
    sub_game      TEXT,
    global_pct    REAL
);

CREATE TABLE guides (
    published_file_id  TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    author        TEXT,
    time_updated  TIMESTAMPTZ,
    votes_up      INTEGER
);

CREATE TABLE chunks (
    id             BIGSERIAL PRIMARY KEY,
    guide_id       TEXT NOT NULL REFERENCES guides(published_file_id) ON DELETE CASCADE,
    section_title  TEXT,
    ordinal        INTEGER NOT NULL,
    text           TEXT NOT NULL,
    sub_game       TEXT,
    embedding      vector(384),
    tsv            tsvector
);

-- ON DELETE CASCADE here (and above) matters for re-runnability: chunk.py
-- deletes and reinserts a guide's chunks every time it runs, and a link
-- in achievement_chunks pointing at a chunk that no longer exists isn't
-- meaningful data worth protecting - it should disappear along with the
-- chunk, not block the delete with a foreign key error.
CREATE TABLE achievement_chunks (
    achievement_id  TEXT NOT NULL REFERENCES achievements(api_name) ON DELETE CASCADE,
    chunk_id        BIGINT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    confidence      REAL,
    method          TEXT,
    PRIMARY KEY (achievement_id, chunk_id)
);
