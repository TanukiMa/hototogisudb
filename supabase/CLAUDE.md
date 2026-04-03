# supabase/ — Database Schema & RPC Reference

## Design Principle: Two-Flag Separation

SSK master "abolition" and Mozc dictionary "exclusion" are **independent concerns**.

| Flag | Meaning | Set by |
|---|---|---|
| `is_active` | Term is still current in the SSK master | Importer (automatic) |
| `dict_enabled` | Term should appear in the Mozc dictionary | Admin (manual) |

An abolished term (`is_active=FALSE`) stays in the dictionary until an admin explicitly sets `dict_enabled=FALSE`.
**The exporter filters on `dict_enabled` only — `is_active` is never used as a filter.**

---

## Tables

### `pos_types` — Mozc POS master

```sql
CREATE TABLE pos_types (
    id          SERIAL PRIMARY KEY,
    left_id     INTEGER NOT NULL,
    right_id    INTEGER NOT NULL,
    description TEXT    NOT NULL,   -- e.g. '名詞固有名詞一般'
    category    TEXT,               -- 'disease' | 'drug' | 'procedure' | 'general'
    UNIQUE (left_id, right_id)
);
```

> ⚠️ Verify actual `left_id` / `right_id` values against `src/data/dictionary_oss/id.def`
> in the Mozc4med repository before populating this table.
> The export RPC looks up POS IDs by `category` at runtime.

---

### `import_batches` — Import history

Provenance is tracked at **batch level** (all records in one CSV share the same source).
`file_sha256` enables duplicate-import prevention and academic citation.

```sql
CREATE TABLE import_batches (
    id            BIGSERIAL PRIMARY KEY,
    source_type   TEXT        NOT NULL,  -- 'ssk_shinryo_koi' | 'ssk_iyakuhin' | 'ssk_shobyomei' | 'custom_csv'
    source_url    TEXT,                  -- e.g. https://www.ssk.or.jp/.../s_ALL20260401.zip
    file_name     TEXT        NOT NULL,  -- e.g. s_ALL20260401.csv (extracted CSV name, not ZIP)
    file_sha256   TEXT,                  -- SHA-256 of the CSV file (after ZIP extraction)
    record_count  INTEGER,
    imported_by   TEXT,                  -- username or 'github-actions'
    imported_at   TIMESTAMPTZ DEFAULT NOW(),
    notes         TEXT
);
```

---

### `ssk_shinryo_koi` — Medical procedure master

Field mapping (`row[field_no - 1]` for 0-indexed access):

| Field no. | Japanese name | Width | Column |
|---|---|---|---|
| 1 | 変更区分 | 1 | `change_type` |
| 3 | 診療行為コード | 9 | `shinryo_koi_code` |
| 5 | 省略漢字名称 | 32 | `abbr_kanji_name` |
| 7 | 省略カナ名称 | 20 | `abbr_kana_name` |
| 87 | 変更年月日 | 8 | `changed_at` |
| 88 | 廃止年月日 | 8 | `abolished_at` |
| 113 | 基本漢字名称 | 64 | `base_kanji_name` |

```sql
CREATE TABLE ssk_shinryo_koi (
    id                  BIGSERIAL PRIMARY KEY,
    shinryo_koi_code    TEXT    NOT NULL UNIQUE,
    abbr_kanji_name     TEXT,   -- surface_form (primary)
    abbr_kana_name      TEXT,   -- stored as-is (CP932→UTF-8 only); normalized at export
    base_kanji_name     TEXT,   -- surface_form fallback
    change_type         TEXT,
    changed_at          DATE,
    abolished_at        DATE,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    dict_enabled        BOOLEAN NOT NULL DEFAULT TRUE,
    batch_id            BIGINT  REFERENCES import_batches(id),
    imported_at         TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_ssk_shinryo_koi_dict  ON ssk_shinryo_koi(dict_enabled);
CREATE INDEX idx_ssk_shinryo_koi_batch ON ssk_shinryo_koi(batch_id);
```

`surface_form`: `abbr_kanji_name` → fallback `base_kanji_name` / `cost` = 5500

---

### `ssk_iyakuhin` — Drug master

| Field no. | Japanese name | Width | Column |
|---|---|---|---|
| 1 | 変更区分 | 1 | `change_type` |
| 3 | 医薬品コード | 9 | `iyakuhin_code` |
| 5 | 漢字名称 | 32 | `kanji_name` |
| 7 | カナ名称 | 20 | `kana_name` |
| 17 | 後発品区分 | 1 | `is_generic` |
| 30 | 変更年月日 | 8 | `changed_at` |
| 31 | 廃止年月日 | 8 | `abolished_at` |
| 35 | 基本漢字名称 | 100 | `base_kanji_name` |
| 37 | 一般名コード | 12 | `generic_name_code` |
| 38 | 一般名処方の標準的な記載 | 100 | `generic_name_label` |

```sql
CREATE TABLE ssk_iyakuhin (
    id                  BIGSERIAL PRIMARY KEY,
    iyakuhin_code       TEXT    NOT NULL UNIQUE,
    kanji_name          TEXT,   -- brand name (surface_form)
    kana_name           TEXT,   -- stored as-is (CP932→UTF-8 only); normalized at export
    base_kanji_name     TEXT,
    generic_name_code   TEXT,
    generic_name_label  TEXT,   -- INN / standard generic prescription label
    is_generic          BOOLEAN,
    change_type         TEXT,
    changed_at          DATE,
    abolished_at        DATE,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    dict_enabled        BOOLEAN NOT NULL DEFAULT TRUE,
    batch_id            BIGINT  REFERENCES import_batches(id),
    imported_at         TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_ssk_iyakuhin_dict         ON ssk_iyakuhin(dict_enabled);
CREATE INDEX idx_ssk_iyakuhin_generic_code ON ssk_iyakuhin(generic_name_code);
CREATE INDEX idx_ssk_iyakuhin_batch        ON ssk_iyakuhin(batch_id);
```

Generates **two TSV entries** per record: `kanji_name` (brand) and `generic_name_label` (INN).
`cost`: originator = 5000, generic (`is_generic=TRUE`) = 5200.

---

### `ssk_shobyomei` — Disease / injury name master

| Field no. | Japanese name | Width | Column |
|---|---|---|---|
| 1 | 変更区分 | 1 | `change_type` |
| 3 | 傷病名コード | 7 | `shobyomei_code` |
| 4 | 移行先コード | 7 | `successor_code` |
| 6 | 傷病名基本名称 | 30 | `base_name` |
| 8 | 傷病名省略名称 | 20 | `abbr_name` |
| 10 | 傷病名カナ名称 | 50 | `kana_name` |
| 11 | 病名管理番号 | 8 | `byomei_mgmt_code` |
| 12 | 採用区分 | 1 | `adoption_type` |
| 16 | ICD-10-1（2013年） | 5 | `icd10_1` |
| 17 | ICD-10-2（2013年） | 5 | `icd10_2` |
| 22 | 収載年月日 | 8 | `listed_at` |
| 23 | 変更年月日 | 8 | `changed_at` |
| 24 | 廃止年月日 | 8 | `abolished_at` |

```sql
CREATE TABLE ssk_shobyomei (
    id                  BIGSERIAL PRIMARY KEY,
    shobyomei_code      TEXT    NOT NULL UNIQUE,
    successor_code      TEXT,
    base_name           TEXT,   -- surface_form (primary)
    abbr_name           TEXT,   -- surface_form fallback
    kana_name           TEXT,   -- stored as-is (CP932→UTF-8 only); normalized at export
    byomei_mgmt_code    TEXT,   -- MEDIS-DC linkage key
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
CREATE INDEX idx_ssk_shobyomei_dict  ON ssk_shobyomei(dict_enabled);
CREATE INDEX idx_ssk_shobyomei_icd10 ON ssk_shobyomei(icd10_1);
CREATE INDEX idx_ssk_shobyomei_mgmt  ON ssk_shobyomei(byomei_mgmt_code);
CREATE INDEX idx_ssk_shobyomei_batch ON ssk_shobyomei(batch_id);
```

`surface_form`: `base_name` → fallback `abbr_name` / `cost` = 4800 (highest priority)

---

### `custom_terms` — Manual / CSV terms

Per-record provenance (`source_url` on the row, not via `import_batches`). No `is_active` flag.

```sql
CREATE TABLE custom_terms (
    id              BIGSERIAL PRIMARY KEY,
    surface_form    TEXT    NOT NULL,
    reading         TEXT    NOT NULL,       -- Hiragana + ASCII digits only
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
```

---

## Pydantic Models (`mozc4med_dict/models.py`)

Importers produce these via `_parse()`; `base.py` serializes them to `dict` for `client.rpc()`.
`batch_id` is **not** in the model — it is injected by `base.py` at write time.

```python
class SskShobyomeiRecord(BaseModel):
    shobyomei_code:   str
    successor_code:   str | None = None
    base_name:        str | None = None
    abbr_name:        str | None = None
    kana_name:        str | None = None
    byomei_mgmt_code: str | None = None
    adoption_type:    str | None = None
    icd10_1:          str | None = None
    icd10_2:          str | None = None
    change_type:      str
    listed_at:        date | None = None
    changed_at:       date | None = None
    abolished_at:     date | None = None
    is_active:        bool = True

class SskIyakuhinRecord(BaseModel):
    iyakuhin_code:      str
    kanji_name:         str | None = None
    kana_name:          str | None = None
    base_kanji_name:    str | None = None
    generic_name_code:  str | None = None
    generic_name_label: str | None = None
    is_generic:         bool = False
    change_type:        str
    changed_at:         date | None = None
    abolished_at:       date | None = None
    is_active:          bool = True

class SskShinryoKoiRecord(BaseModel):
    shinryo_koi_code: str
    abbr_kanji_name:  str | None = None
    abbr_kana_name:   str | None = None
    base_kanji_name:  str | None = None
    change_type:      str
    changed_at:       date | None = None
    abolished_at:     date | None = None
    is_active:        bool = True
```

---

## UPSERT RPC (`migrations/20260101000007_create_upsert_rpcs.sql`)

Defines one function per SSK table. Each performs `INSERT … ON CONFLICT DO UPDATE SET`
**without** `dict_enabled`, preserving admin intent on re-import.

```sql
-- Example: ssk_shobyomei. Repeat pattern for ssk_iyakuhin and ssk_shinryo_koi.
CREATE OR REPLACE FUNCTION upsert_ssk_shobyomei(records JSONB, p_batch_id BIGINT)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE rec JSONB;
BEGIN
    FOR rec IN SELECT * FROM jsonb_array_elements(records) LOOP
        INSERT INTO ssk_shobyomei (
            shobyomei_code, successor_code, base_name, abbr_name, kana_name,
            byomei_mgmt_code, adoption_type, icd10_1, icd10_2,
            change_type, listed_at, changed_at, abolished_at,
            is_active, dict_enabled, batch_id
        ) VALUES (
            rec->>'shobyomei_code', rec->>'successor_code',
            rec->>'base_name',      rec->>'abbr_name',
            rec->>'kana_name',      rec->>'byomei_mgmt_code',
            rec->>'adoption_type',  rec->>'icd10_1', rec->>'icd10_2',
            rec->>'change_type',
            (rec->>'listed_at')::date, (rec->>'changed_at')::date,
            (rec->>'abolished_at')::date,
            (rec->>'is_active')::boolean,
            TRUE,        -- dict_enabled=TRUE for new records only
            p_batch_id
        )
        ON CONFLICT (shobyomei_code) DO UPDATE SET
            successor_code = EXCLUDED.successor_code, base_name = EXCLUDED.base_name,
            abbr_name = EXCLUDED.abbr_name,           kana_name = EXCLUDED.kana_name,
            byomei_mgmt_code = EXCLUDED.byomei_mgmt_code,
            adoption_type = EXCLUDED.adoption_type,
            icd10_1 = EXCLUDED.icd10_1,               icd10_2 = EXCLUDED.icd10_2,
            change_type = EXCLUDED.change_type,
            listed_at = EXCLUDED.listed_at,            changed_at = EXCLUDED.changed_at,
            abolished_at = EXCLUDED.abolished_at,      is_active = EXCLUDED.is_active,
            batch_id = EXCLUDED.batch_id,              imported_at = NOW()
            -- dict_enabled intentionally omitted
        ;
    END LOOP;
END;
$$;
```

## Export RPC (`migrations/20260101000008_create_export_rpc.sql`)

`export_mozc_dict()` returns all `dict_enabled=TRUE` entries as a unified result set.
POS IDs are looked up from `pos_types` by `category` at runtime.

```sql
CREATE TYPE mozc_entry AS (
    raw_reading TEXT, left_id INTEGER, right_id INTEGER, cost INTEGER, surface_form TEXT
);

CREATE OR REPLACE FUNCTION export_mozc_dict()
RETURNS SETOF mozc_entry LANGUAGE sql STABLE AS $$
    SELECT s.kana_name, p.left_id, p.right_id, 4800,
           COALESCE(s.base_name, s.abbr_name)
    FROM ssk_shobyomei s
    CROSS JOIN LATERAL (SELECT left_id, right_id FROM pos_types WHERE category='disease' LIMIT 1) p
    WHERE s.dict_enabled = TRUE AND COALESCE(s.base_name, s.abbr_name) IS NOT NULL
    UNION ALL
    SELECT i.kana_name, p.left_id, p.right_id,
           CASE WHEN i.is_generic THEN 5200 ELSE 5000 END, i.kanji_name
    FROM ssk_iyakuhin i
    CROSS JOIN LATERAL (SELECT left_id, right_id FROM pos_types WHERE category='drug' LIMIT 1) p
    WHERE i.dict_enabled = TRUE AND i.kanji_name IS NOT NULL
    UNION ALL
    SELECT i.kana_name, p.left_id, p.right_id,
           CASE WHEN i.is_generic THEN 5200 ELSE 5000 END, i.generic_name_label
    FROM ssk_iyakuhin i
    CROSS JOIN LATERAL (SELECT left_id, right_id FROM pos_types WHERE category='drug' LIMIT 1) p
    WHERE i.dict_enabled = TRUE AND i.generic_name_label IS NOT NULL
    UNION ALL
    SELECT k.abbr_kana_name, p.left_id, p.right_id, 5500,
           COALESCE(k.abbr_kanji_name, k.base_kanji_name)
    FROM ssk_shinryo_koi k
    CROSS JOIN LATERAL (SELECT left_id, right_id FROM pos_types WHERE category='procedure' LIMIT 1) p
    WHERE k.dict_enabled = TRUE AND COALESCE(k.abbr_kanji_name, k.base_kanji_name) IS NOT NULL
    UNION ALL
    SELECT c.reading,
           COALESCE(p.left_id,  (SELECT left_id  FROM pos_types WHERE category='general' LIMIT 1)),
           COALESCE(p.right_id, (SELECT right_id FROM pos_types WHERE category='general' LIMIT 1)),
           c.cost, c.surface_form
    FROM custom_terms c
    LEFT JOIN pos_types p ON c.pos_type_id = p.id
    WHERE c.dict_enabled = TRUE;
$$;
```
