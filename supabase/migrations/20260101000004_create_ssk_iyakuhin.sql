CREATE TABLE IF NOT EXISTS ssk_iyakuhin (
    id                  BIGSERIAL PRIMARY KEY,
    iyakuhin_code       TEXT    NOT NULL UNIQUE,
    kanji_name          TEXT,
    kana_name           TEXT,
    base_kanji_name     TEXT,
    generic_name_code   TEXT,
    generic_name_label  TEXT,
    is_generic          BOOLEAN,
    change_type         TEXT,
    changed_at          DATE,
    abolished_at        DATE,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    dict_enabled        BOOLEAN NOT NULL DEFAULT TRUE,
    batch_id            BIGINT  REFERENCES import_batches(id),
    imported_at         TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ssk_iyakuhin_dict         ON ssk_iyakuhin(dict_enabled);
CREATE INDEX IF NOT EXISTS idx_ssk_iyakuhin_generic_code ON ssk_iyakuhin(generic_name_code);
CREATE INDEX IF NOT EXISTS idx_ssk_iyakuhin_batch        ON ssk_iyakuhin(batch_id);
