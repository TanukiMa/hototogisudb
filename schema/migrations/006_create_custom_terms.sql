CREATE TABLE IF NOT EXISTS custom_terms (
    id              BIGSERIAL PRIMARY KEY,
    surface_form    TEXT    NOT NULL,
    reading         TEXT    NOT NULL,
    pos_type_id     INTEGER REFERENCES pos_types(id),
    cost            INTEGER NOT NULL DEFAULT 5000,
    source_label    TEXT,
    source_url      TEXT,
    notes           TEXT,
    dict_enabled    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (surface_form, reading)
);
