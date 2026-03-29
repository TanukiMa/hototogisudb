CREATE TABLE IF NOT EXISTS ssk_shinryo_koi (
    id                  BIGSERIAL PRIMARY KEY,
    shinryo_koi_code    TEXT    NOT NULL UNIQUE,
    abbr_kanji_name     TEXT,
    abbr_kana_name      TEXT,
    base_kanji_name     TEXT,
    change_type         TEXT,
    changed_at          DATE,
    abolished_at        DATE,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    dict_enabled        BOOLEAN NOT NULL DEFAULT TRUE,
    batch_id            BIGINT  REFERENCES import_batches(id),
    imported_at         TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ssk_shinryo_koi_dict  ON ssk_shinryo_koi(dict_enabled);
CREATE INDEX IF NOT EXISTS idx_ssk_shinryo_koi_batch ON ssk_shinryo_koi(batch_id);
