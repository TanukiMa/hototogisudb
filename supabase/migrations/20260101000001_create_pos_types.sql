CREATE TABLE IF NOT EXISTS pos_types (
    id          SERIAL PRIMARY KEY,
    left_id     INTEGER NOT NULL,
    right_id    INTEGER NOT NULL,
    description TEXT    NOT NULL,
    category    TEXT,
    UNIQUE (left_id, right_id)
);
