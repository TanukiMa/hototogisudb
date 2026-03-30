CREATE TABLE IF NOT EXISTS ssk_shobyomei (
    id                  BIGSERIAL PRIMARY KEY,
    shobyomei_code      TEXT    NOT NULL UNIQUE,
    successor_code      TEXT,
    base_name           TEXT,
    abbr_name           TEXT,
    kana_name           TEXT,
    byomei_mgmt_code    TEXT,
    adoption_type       TEXT,
    icd10_1             TEXT,
    icd10_2             TEXT,
    change_type         TEXT,
    listed_at           DATE,
    changed_at          DATE,
    abolished_at        DATE,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    dict_enabled        BOOLEAN NOT NULL DEFAULT TRUE,
    batch_id            BIGINT  REFERENCES import_batches(id),
    imported_at         TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ssk_shobyomei_dict  ON ssk_shobyomei(dict_enabled);
CREATE INDEX IF NOT EXISTS idx_ssk_shobyomei_icd10 ON ssk_shobyomei(icd10_1);
CREATE INDEX IF NOT EXISTS idx_ssk_shobyomei_mgmt  ON ssk_shobyomei(byomei_mgmt_code);
CREATE INDEX IF NOT EXISTS idx_ssk_shobyomei_batch ON ssk_shobyomei(batch_id);
