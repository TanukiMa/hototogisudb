CREATE TABLE IF NOT EXISTS import_batches (
    id            BIGSERIAL PRIMARY KEY,
    source_type   TEXT        NOT NULL,
    source_url    TEXT,
    file_name     TEXT        NOT NULL,
    file_sha256   TEXT,
    record_count  INTEGER,
    imported_by   TEXT,
    imported_at   TIMESTAMPTZ DEFAULT NOW(),
    notes         TEXT
);
