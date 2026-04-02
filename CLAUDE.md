# Mozc4med Medical Terminology Database

## Project Overview

A database system for managing Japanese medical terminology used in Mozc4med
(a medically enhanced fork of the Mozc IME).
Terms are stored in Supabase (PostgreSQL) and exported as a Mozc **system dictionary TSV**.
Dictionary export is automated via **GitHub Actions**, which commits the generated file back to the repository.

### Data Sources

| Source | Master type | Provider |
|---|---|---|
| Medical procedure master (診療行為マスター) | `S` | Social Insurance Medical Fee Payment Fund (SSK) |
| Drug master (医薬品マスター) | `Y` | Social Insurance Medical Fee Payment Fund (SSK) |
| Disease/injury name master (傷病名マスター) | `B` | Social Insurance Medical Fee Payment Fund (SSK) |
| Manual input / CSV import | — | Custom terms |

**Common SSK file specification**: Shift-JIS (cp932), comma-delimited, numeric fields without leading zeros.
Download page: https://www.ssk.or.jp/seikyushiharai/tensuhyo/kihonmasta/

### Output Format — Mozc System Dictionary

```
reading\tleft_id\tright_id\tcost\tsurface_form
```

| Field | Description | Example |
|---|---|---|
| `reading` | Hiragana + ASCII digits | `とうにょうびょう` |
| `left_id` | Left context POS ID (from `id.def`) | `1849` |
| `right_id` | Right context POS ID (from `id.def`) | `1849` |
| `cost` | Generation cost (0–10000; lower = higher priority) | `4800` |
| `surface_form` | Display form | `糖尿病` |

---

## Directory Structure

```
mozc4med-dict/
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── cliff.toml
├── .env.example
├── .env                            # gitignored
├── .github/workflows/
│   ├── ci.yml
│   ├── export_mozc_dict.yml
│   ├── import_ssk_master.yml
│   ├── supabase_keepalive.yml
│   └── update_changelog.yml
├── dist/
│   └── mozc4med_medical.txt
├── supabase/migrations/
│   ├── 20260101000001_create_pos_types.sql
│   ├── 20260101000002_create_import_batches.sql
│   ├── 20260101000003_create_ssk_shinryo_koi.sql
│   ├── 20260101000004_create_ssk_iyakuhin.sql
│   ├── 20260101000005_create_ssk_shobyomei.sql
│   ├── 20260101000006_create_custom_terms.sql
│   ├── 20260101000008_create_export_rpc.sql    # export_mozc_dict() UNION ALL function
│   └── 20260101000009_create_upsert_rpcs.sql   # per-table UPSERT functions (dict_enabled safe)
├── mozc4med_dict/
│   ├── __init__.py
│   ├── db.py
│   ├── models.py                   # Pydantic v2 models for SSK records
│   ├── utils/
│   │   ├── __init__.py
│   │   └── kana.py                 # normalize_reading() — export-time only
│   ├── importers/
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseImporter ABC
│   │   ├── ssk_shinryo_koi.py
│   │   ├── ssk_iyakuhin.py
│   │   ├── ssk_shobyomei.py
│   │   └── csv_generic.py
│   └── exporters/
│       ├── __init__.py
│       └── mozc_system_dict.py
├── scripts/
│   ├── import_shinryo_koi.py
│   ├── import_iyakuhin.py
│   ├── import_shobyomei.py
│   ├── import_csv.py
│   ├── export_mozc_dict.py
│   ├── manage_dict_enabled.py
│   └── supabase_keepalive.py
└── tests/
    ├── unit/
    │   ├── test_kana.py
    │   ├── test_importer_base.py
    │   ├── test_ssk_shobyomei.py
    │   ├── test_ssk_iyakuhin.py
    │   ├── test_ssk_shinryo_koi.py
    │   └── test_mozc_exporter.py
    └── integration/
        ├── conftest.py
        ├── test_import_shobyomei.py
        ├── test_import_iyakuhin.py
        ├── test_import_shinryo_koi.py
        ├── test_upsert_no_overwrite_dict_enabled.py
        ├── test_sha256_dedup.py
        └── test_export_pipeline.py
```

Each package directory (`mozc4med_dict/`, `utils/`, `importers/`, `exporters/`) must contain `__init__.py`.

---

## Setup & Dependencies

### `pyproject.toml`

```toml
[project]
dependencies = [
    "supabase>=2.0",        # supabase-py — official Supabase Python client
    "python-dotenv>=1.0",
    "pydantic>=2.0",
    "alphabet2kana>=1.0",   # ASCII [a-z][A-Z] → katakana ("DX" → "ディーエックス")
    "jaconv>=0.3",          # Kana conversion: hankaku→zenkaku, kata→hira
]

[project.optional-dependencies]
dev = ["pytest", "pytest-mock", "ruff", "mypy"]

[project.scripts]
mozc4med-import-shinryo-koi = "scripts.import_shinryo_koi:main"
mozc4med-import-iyakuhin    = "scripts.import_iyakuhin:main"
mozc4med-import-shobyomei   = "scripts.import_shobyomei:main"
mozc4med-import-csv         = "scripts.import_csv:main"
mozc4med-export             = "scripts.export_mozc_dict:main"
mozc4med-keepalive          = "scripts.supabase_keepalive:main"

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true
```

---

## Credentials & Secrets Management

| Environment | Source |
|---|---|
| Local development | `.env` file (copy from `.env.example`) |
| GitHub Actions | `secrets.*` injected as env vars |

```dotenv
# .env.example — safe to commit
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

Register all four secrets in **Settings → Secrets and variables → Actions**:

| Secret | Purpose |
|---|---|
| `SUPABASE_URL` | Production project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Full read/write access (production) |
| `SUPABASE_TEST_URL` | Dedicated test project URL |
| `SUPABASE_TEST_SERVICE_ROLE_KEY` | Full read/write access (test) |

> ⚠️ `SERVICE_ROLE_KEY` bypasses RLS. Never expose it in logs or `run:` step output.
> In GHA workflows, always pass secrets via `env:` — never interpolate `${{ secrets.* }}` inside `run:`.

```yaml
# Correct pattern for all workflows
- name: Run script
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
  run: python scripts/some_script.py
```

### `mozc4med_dict/db.py`

```python
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()  # No-op on GHA; loads .env locally. Call once, here only.

def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]            # KeyError immediately if not set
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)
```

Use `os.environ["KEY"]` (not `os.getenv`) for immediate `KeyError` on missing secrets.
Always access Supabase through `get_client()` — never instantiate the client directly.
For `dict_enabled`-safe UPSERT and multi-table `UNION ALL`, use `client.rpc()` — not `.upsert()`.

---

## Database Schema

### Design Principle: Two-Flag Separation

SSK master "abolition" and Mozc dictionary "exclusion" are **independent concerns**.

| Flag | Meaning | Set by |
|---|---|---|
| `is_active` | Term is still current in the SSK master | Importer (automatic) |
| `dict_enabled` | Term should appear in the Mozc dictionary | Admin (manual) |

An abolished term (`is_active=FALSE`) stays in the dictionary until an admin explicitly sets `dict_enabled=FALSE`.
**The exporter filters on `dict_enabled` only — `is_active` is never used as a filter.**

---

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
    source_url    TEXT,                  -- e.g. https://www.ssk.or.jp/.../kihonmasta_07.html
    file_name     TEXT        NOT NULL,  -- e.g. b_ALL20260325.csv
    file_sha256   TEXT,                  -- SHA-256 of raw file
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

## Models (`mozc4med_dict/models.py`)

Pydantic v2 models represent parsed SSK records before DB write.
Importers produce these via `_parse()`; `base.py` serializes them to `dict` for `client.rpc()`.
`batch_id` is **not** in the model — it is injected by `base.py` at write time.

```python
from pydantic import BaseModel
from datetime import date

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

## Importer Specification

### Character Encoding Policy

**Import-time: CP932 → UTF-8 only. All kana normalization is deferred to export.**

SSK kana fields contain mixed content in practice. Confirmed real-world examples:

| Term | kana_name value | Content |
|---|---|---|
| 医療DX | `ｲﾘｮｳDX` | Half-width kana + ASCII uppercase |
| 1型糖尿病 | `1ｶﾞﾀﾄｳﾆｮｳﾋﾞｮｳ` | ASCII digit + half-width dakuten kana |

Storing raw values preserves original data for audit/citation and allows `normalize_reading()` to be improved without re-importing.

### `BaseImporter` Interface (`importers/base.py`)

All SSK importers must subclass `BaseImporter` and implement only `_parse()`.
SHA-256, batch creation, and UPSERT are owned by the base class — never re-implement them in a subclass.

```python
import hashlib, csv
from abc import ABC, abstractmethod
from pathlib import Path
from supabase import Client
from mozc4med_dict.db import get_client

class BaseImporter(ABC):
    source_type: str  # 'ssk_shobyomei' | 'ssk_iyakuhin' | 'ssk_shinryo_koi'

    def run(self, file: Path, url: str, imported_by: str = "local") -> int:
        """Execute full import pipeline. Returns number of records imported."""
        client = get_client()
        sha256 = self._sha256(file)
        self._abort_if_duplicate(client, sha256)
        batch_id = self._create_batch(client, file, url, sha256, imported_by)
        records = self._parse(file)
        self._upsert(client, records, batch_id)
        client.table("import_batches").update({"record_count": len(records)}) \
              .eq("id", batch_id).execute()
        return len(records)

    @abstractmethod
    def _parse(self, file: Path) -> list[dict]:
        """Parse CP932 CSV → list of record dicts. batch_id must NOT be included."""
        ...

    def _upsert(self, client: Client, records: list[dict], batch_id: int) -> None:
        """UPSERT via Postgres RPC.

        supabase-py's .upsert() updates ALL columns, which would overwrite dict_enabled.
        The RPC omits dict_enabled from DO UPDATE SET, preserving admin intent.
        """
        client.rpc(f"upsert_{self.source_type}",
                   {"records": records, "p_batch_id": batch_id}).execute()

    def _sha256(self, file: Path) -> str:
        h = hashlib.sha256()
        with open(file, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _abort_if_duplicate(self, client: Client, sha256: str) -> None:
        result = client.table("import_batches").select("id") \
                       .eq("file_sha256", sha256).execute()
        if result.data:
            raise ValueError(f"Already imported: file_sha256={sha256}")

    def _create_batch(self, client: Client, file: Path, url: str,
                      sha256: str, imported_by: str) -> int:
        result = client.table("import_batches").insert({
            "source_type": self.source_type,
            "source_url":  url,
            "file_name":   file.name,
            "file_sha256": sha256,
            "imported_by": imported_by,
        }).execute()
        return result.data[0]["id"]
```

**Subclass example** (`importers/ssk_shobyomei.py`):

```python
class SskShobyomeiImporter(BaseImporter):
    source_type = "ssk_shobyomei"

    def _parse(self, file: Path) -> list[dict]:
        records = []
        with open(file, encoding="cp932") as f:
            for row in csv.reader(f):
                rec = SskShobyomeiRecord(
                    shobyomei_code = row[2],          # field 3  → index 2
                    successor_code = row[3] or None,
                    base_name      = row[5] or None,
                    abbr_name      = row[7] or None,
                    kana_name      = row[9] or None,
                    # ... remaining fields
                    change_type    = row[0],
                    is_active      = (row[23] == ""), # empty abolished_at → active
                )
                records.append(rec.model_dump())
        return records
```

### `change_type` Handling

`change_type` determines `is_active` in the parsed dict (set in `_parse()`).
`dict_enabled` is **never set in `_parse()`** — the RPC sets it `TRUE` for new records only;
existing records keep their current value.

| change_type | is_active |
|---|---|
| `1` (new) | `True` |
| `3` (modified) | `True` |
| `4` (abolished) | `False` |

### UPSERT RPC (`supabase/migrations/20260101000007_create_upsert_rpcs.sql`)

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

### Custom CSV Import (`importers/csv_generic.py`)

Imports into `custom_terms`. Input CSV: UTF-8, LF, headers case-sensitive.

```csv
surface_form,reading,cost,pos_category,source_url,notes
糖尿病性腎症,とうにょうびょうせいじんしょう,4900,disease,,
アモキシシリン,あもきししりん,5000,drug,https://example.com/,
```

| Column | Required | Description |
|---|---|---|
| `surface_form` | ✓ | Display form |
| `reading` | ✓ | Hiragana + ASCII digits (pre-validated; `normalize_reading()` is not called) |
| `cost` | — | Default: 5000 |
| `pos_category` | — | `disease` / `drug` / `procedure` / `general`; maps to `pos_types.category` |
| `source_url` | — | Origin URL |
| `notes` | — | Free text |

---

## Exporter Specification

### Export RPC (`supabase/migrations/20260101000008_create_export_rpc.sql`)

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

### Python Exporter (`exporters/mozc_system_dict.py`)

```python
from pathlib import Path
import logging
from mozc4med_dict.db import get_client
from mozc4med_dict.utils.kana import normalize_reading

logger = logging.getLogger(__name__)

def export(output: Path) -> tuple[int, int]:
    """Export dictionary TSV. Returns (written, skipped)."""
    client = get_client()
    rows = client.rpc("export_mozc_dict", {}).execute().data
    written = skipped = 0
    with open(output, "w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            try:
                reading = normalize_reading(row["raw_reading"])
            except ValueError as e:
                logger.warning("skipped: %s (surface=%s)", e, row["surface_form"])
                skipped += 1
                continue
            f.write(f"{reading}\t{row['left_id']}\t{row['right_id']}"
                    f"\t{row['cost']}\t{row['surface_form']}\n")
            written += 1
    logger.info("export complete: %d written, %d skipped", written, skipped)
    return written, skipped
```

### `utils/kana.py` — `normalize_reading()`

Called **only in `mozc_system_dict.py`** at export time.
Not called for `custom_terms` (reading is pre-validated at import).

**Conversion pipeline**:

```
Input (raw DB value, UTF-8)
  ├─ 1. 全角カタカナ → 平仮名          jaconv.kata2hira()
  ├─ 2. 半角カナ（濁点合成含む）→ 全角カタカナ → 平仮名
  │       jaconv.h2z(kana=True) → jaconv.kata2hira()
  │       例: ｶﾞ→ガ→が、ｲﾘｮｳ→イリョウ→いりょう
  ├─ 3. ASCII [a-z][A-Z] → カタカナ → 平仮名
  │       alphabet2kana.alphabet2kana() → jaconv.kata2hira()
  │       例: DX→ディーエックス→でぃーえっくす
  ├─ 4. ASCII [0-9] → そのまま通す（Mozc 側に委ねる）
  │       例: 1ｶﾞﾀﾄｳﾆｮｳﾋﾞｮｳ → 1がたとうにょうびょう
  └─ 5. その他の残留文字（漢字・記号・全角英数等）→ ValueError
```

```python
import unicodedata, jaconv, alphabet2kana

def normalize_reading(raw: str) -> str:
    """Output: hiragana + ASCII digits only. Raises ValueError otherwise."""
    if not raw:
        raise ValueError("empty reading")
    s = jaconv.kata2hira(raw)
    s = jaconv.kata2hira(jaconv.h2z(s, kana=True))
    s = jaconv.kata2hira(alphabet2kana.alphabet2kana(s))
    for ch in s:
        if ch.isascii() and ch.isdigit():
            continue
        if unicodedata.name(ch, "").startswith("HIRAGANA"):
            continue
        raise ValueError(f"unexpected character {ch!r} in {s!r} (raw={raw!r})")
    return s
```

> ⚠️ `alphabet2kana` の変換結果はバージョン依存。ユニットテストでは「平仮名＋半角数字のみ」
> であることを優先して検証し、特定の変換文字列は回帰テストとして別途追加する。

**Unit test cases**:

| Input | Expected output | Notes |
|---|---|---|
| `イリョウ` | `いりょう` | 全角カタカナ |
| `ｲﾘｮｳ` | `いりょう` | 半角カナ |
| `ｶﾞﾀ` | `がた` | 半角濁点合成 |
| `ｲﾘｮｳDX` | `いりょう` + hira("DX") | ASCII英字変換（実確認例） |
| `1ｶﾞﾀﾄｳﾆｮｳﾋﾞｮｳ` | `1がたとうにょうびょう` | 数字通過（実確認例） |
| `漢字` | `ValueError` | 非カナ・非数字 |
| `` (empty) | `ValueError` | 空文字列 |

---

## GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|---|---|---|
| `ci.yml` | PR to `main` | Lint → unit tests → integration tests |
| `export_mozc_dict.yml` | Weekly (Mon 02:00 UTC) + manual | Export dictionary, commit back |
| `import_ssk_master.yml` | Manual only | Import SSK master CSV |
| `supabase_keepalive.yml` | Daily (00:00 UTC) | Prevent free-tier freeze |
| `update_changelog.yml` | Push to `main` | Regenerate CHANGELOG.md via git-cliff |

### `ci.yml`

```yaml
name: CI
on:
  pull_request:
    branches: [main]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e ".[dev]"
      - run: ruff check . && mypy mozc4med_dict/

  unit-tests:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e ".[dev]"
      - run: pytest tests/unit/ -v

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests           # Gate on unit tests to avoid burning Supabase API quota
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e ".[dev]"
      - name: Run integration tests
        env:
          SUPABASE_TEST_URL: ${{ secrets.SUPABASE_TEST_URL }}
          SUPABASE_TEST_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_TEST_SERVICE_ROLE_KEY }}
        run: pytest tests/integration/ -v
```

### `export_mozc_dict.yml`

```yaml
name: Export Mozc Dictionary
on:
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * 1'    # Mon 02:00 UTC (JST 11:00)
jobs:
  export:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e .
      - name: Export
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
        run: python scripts/export_mozc_dict.py --output dist/mozc4med_medical.txt
      - name: Commit and push
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add dist/mozc4med_medical.txt
          git diff --cached --quiet || git commit -m "chore: update mozc4med_medical.txt"
          git push
```

### `import_ssk_master.yml`

```yaml
name: Import SSK Master
on:
  workflow_dispatch:
    inputs:
      master_type:
        description: 'Master type'
        required: true
        type: choice
        options: [shinryo_koi, iyakuhin, shobyomei]
      file_url:
        description: 'Direct URL to CSV file'
        required: true
        type: string
jobs:
  import:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e .
      - run: curl -fsSL "${{ inputs.file_url }}" -o master.csv
      - name: Import
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
        run: |
          python scripts/import_${{ inputs.master_type }}.py \
            --file master.csv --url "${{ inputs.file_url }}" --imported-by "github-actions"
```

### `supabase_keepalive.yml`

```yaml
name: Supabase Keep-Alive
on:
  schedule:
    - cron: '0 0 * * *'    # Daily 00:00 UTC (JST 09:00)
  workflow_dispatch:
jobs:
  keepalive:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e .
      - name: Ping
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
        run: python scripts/supabase_keepalive.py
```

`supabase_keepalive.py`: `client.table("import_batches").select("id").limit(1).execute()` — read-only ping, no writes.

### `update_changelog.yml`

```yaml
name: Update Changelog
on:
  push:
    branches: [main]
jobs:
  changelog:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - name: Generate CHANGELOG.md
        uses: orhun/git-cliff-action@v3
        with: { config: cliff.toml, args: --verbose }
        env: { OUTPUT: CHANGELOG.md }
      - run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add CHANGELOG.md
          git diff --cached --quiet || git commit -m "docs: update CHANGELOG.md [skip ci]"
          git push
```

> `[skip ci]` prevents CI from re-triggering on the auto-generated commit.

---

## CLI Reference

```bash
# Import SSK masters
python scripts/import_shinryo_koi.py --file data/s_ALL20260325.csv --url "https://..."
python scripts/import_iyakuhin.py    --file data/y_ALL20260325.csv --url "https://..."
python scripts/import_shobyomei.py   --file data/b_ALL20260325.csv --url "https://..."
python scripts/import_csv.py         --file data/custom_terms.csv  --source "Custom terms v1"

# Export
python scripts/export_mozc_dict.py --output dist/mozc4med_medical.txt
python scripts/export_mozc_dict.py --dry-run    # Count only, no file written
gh workflow run export_mozc_dict.yml             # Trigger GHA manually

# Manage dict_enabled
python scripts/manage_dict_enabled.py --list-abolished
python scripts/manage_dict_enabled.py --disable 1234567             # 7桁 → ssk_shobyomei
python scripts/manage_dict_enabled.py --disable 123456789 --table shinryo_koi  # 9桁は --table 必須
python scripts/manage_dict_enabled.py --disable 123456789 --table iyakuhin
python scripts/manage_dict_enabled.py --enable  1234567
```

`manage_dict_enabled.py` のコード長による自動判別:

| コード長 | `--table` | 対象テーブル |
|---|---|---|
| 7桁 | 不要 | `ssk_shobyomei` |
| 9桁 | `shinryo_koi` | `ssk_shinryo_koi` |
| 9桁 | `iyakuhin` | `ssk_iyakuhin` |
| 9桁 | 省略 | エラーで終了 |

---

## Verification & Testing

```bash
ruff check . --fix && mypy mozc4med_dict/
pytest tests/unit/ -v
pytest tests/integration/ -v   # requires SUPABASE_TEST_* env vars
pytest -v                      # all
```

### Unit Test Key Cases

Unit tests must run with **no network access** — mock `db.get_client()` with `pytest-mock`.

| Module | What to test |
|---|---|
| `utils/kana.py` | All cases in the normalize_reading() test table above |
| `importers/base.py` | `_sha256()` correctness; `_abort_if_duplicate()` raises on existing hash; `change_type=4` → `is_active=False`; `dict_enabled` absent from `_parse()` output |
| `exporters/mozc_system_dict.py` | TSV format (tab-delimited, 5 fields); correct cost per source; UTF-8 LF; `ValueError` rows skipped and counted |

### Integration Test Key Cases

Tests use `SUPABASE_TEST_*` credentials — never production.
Schema must be kept in sync with `supabase/migrations/` (apply every new migration to the test project).

`tests/integration/conftest.py` pattern:

```python
@pytest.fixture(scope="session")
def client() -> Client:
    return create_client(os.environ["SUPABASE_TEST_URL"],
                         os.environ["SUPABASE_TEST_SERVICE_ROLE_KEY"])

@pytest.fixture(autouse=True)
def truncate_tables(client):
    for table in ["ssk_shobyomei", "ssk_iyakuhin", "ssk_shinryo_koi",
                  "custom_terms", "import_batches"]:
        client.table(table).delete().neq("id", 0).execute()
```

**Critical test — `dict_enabled` must survive re-import**
(implement for all three SSK importers in `test_upsert_no_overwrite_dict_enabled.py`):

```python
def test_upsert_does_not_overwrite_dict_enabled(client):
    importer = SskShobyomeiImporter()
    importer.run(sample_csv, url="https://example.com", imported_by="test")
    client.table("ssk_shobyomei").update({"dict_enabled": False}) \
          .eq("shobyomei_code", SAMPLE_CODE).execute()
    importer.run(sample_csv_v2, url="https://example.com/v2", imported_by="test")
    row = client.table("ssk_shobyomei").select("dict_enabled") \
                .eq("shobyomei_code", SAMPLE_CODE).single().execute().data
    assert row["dict_enabled"] is False
```

---

## README.md Maintenance

Generate `README.md` at project initialization. **Update in the same commit** when any of the following change:

| Change | README section |
|---|---|
| New / changed CLI flag | Importing / Exporting / Managing |
| New table or column | Database Schema |
| New workflow or changed trigger | GitHub Actions Workflows |
| New dependency | Requirements / Setup |
| Changed cost values or POS mapping | Database Schema |
| Changed `normalize_reading()` policy | Exporting |

**Required sections**: Requirements, Setup, Importing SSK Masters, Exporting, Managing dict_enabled, Running Tests, Database Schema, GitHub Actions Workflows, License.

---

## CHANGELOG.md

Auto-generated by [git-cliff](https://github.com/orhun/git-cliff) on push to `main`.
Commit messages must follow [Conventional Commits](https://www.conventionalcommits.org/).

| Prefix | Group | Example |
|---|---|---|
| `feat:` | Features | `feat: add ssk_iyakuhin importer with dual-entry generation` |
| `fix:` | Bug Fixes | `fix: normalize half-width katakana in kana.py` |
| `schema:` | Schema Changes | `schema: add upsert_ssk_shobyomei RPC` |
| `chore:` | Chores | `chore: update mozc4med_medical.txt` |
| `docs:` | Documentation | `docs: update README CLI reference` |
| `test:` | Tests | `test: add dict_enabled upsert invariant test` |
| `refactor:` | Refactor | `refactor: extract normalize_reading to kana.py` |

### `cliff.toml`

```toml
[changelog]
header = "# Changelog\n\nAll notable changes to mozc4med-dict are documented here.\n"
body = """
{% for group, commits in commits | group_by(attribute="group") %}
### {{ group }}
{% for commit in commits %}
- {{ commit.message }} ([{{ commit.id | truncate(length=7, end="") }}](../../commit/{{ commit.id }}))
{% endfor %}
{% endfor %}
"""
trim = true

[git]
conventional_commits = true
filter_unconventional = true
commit_parsers = [
  { message = "^feat",     group = "Features"       },
  { message = "^fix",      group = "Bug Fixes"      },
  { message = "^schema",   group = "Schema Changes" },
  { message = "^chore",    group = "Chores"         },
  { message = "^docs",     group = "Documentation"  },
  { message = "^test",     group = "Tests"          },
  { message = "^refactor", group = "Refactor"       },
]
```

---

## Cross-Platform Compatibility

All code must run on **Windows, macOS, and Linux** without modification.

- **Paths**: always `pathlib.Path` — never string concatenation with `/` or `\`
- **File encoding**: always specify `encoding=` explicitly
  - SSK CSV input: `encoding="cp932"`
  - Dictionary output: `encoding="utf-8", newline="\n"` (force LF)
- **CLI scripts**: `argparse` only — no shell syntax (`&&`, `export`, backticks)

`.gitattributes`:
```
dist/mozc4med_medical.txt  text eol=lf
*.py text eol=lf  *.sql text eol=lf  *.md text eol=lf  *.toml text eol=lf  *.yml text eol=lf
```

---

## Development Rules & Instructions for Claude Code

**Invariants** (never violate):

1. **Import-time: CP932 → UTF-8 only.** `normalize_reading()` is called only in `mozc_system_dict.py`.
2. **UPSERT via `client.rpc()` only.** `.upsert()` overwrites all columns; the Postgres RPC protects `dict_enabled`.
3. **`dict_enabled` は `DO UPDATE SET` に含めない。** Python 側でも設定しない。新規レコードへの `TRUE` 設定は RPC が行う。
4. **Soft-delete only.** Use `dict_enabled=FALSE` to exclude. Never `DELETE` rows from SSK tables.
5. **Credentials from `os.environ["KEY"]` only.** Never hardcode; never `os.getenv`.
6. **SHA-256 dedup** is handled by `BaseImporter._abort_if_duplicate()` — never re-implement.

**Implementation rules**:

7. All SSK importers subclass `BaseImporter` and implement only `_parse()`. Never re-implement `run()`, `_upsert()`, `_sha256()`, `_create_batch()` in a subclass.
8. `custom_terms` の `reading` はインポート時に平仮名であることを前提とし、`normalize_reading()` を通さない。
9. SSK fields: `row[field_no - 1]` (0-indexed; field numbers from SSK PDF spec).
10. POS IDs: populate `pos_types` from `src/data/dictionary_oss/id.def`; export RPC looks up by `category` at runtime.
11. Migrations: timestamp-prefixed SQL in `supabase/migrations/`; apply to test project on every addition.
12. **Cross-platform**: `pathlib.Path`; explicit `encoding=`; `newline="\n"` for output files.

**Process rules**:

13. `load_dotenv()` once only, at top of `db.py`.
14. In GHA workflows, secrets via `env:` only — never `${{ secrets.* }}` inside `run:`.
15. Raise exceptions in library code; log and handle at the script layer.
16. Run `pytest tests/unit/` before touching integration tests (no network in unit tests; mock `db.get_client()`).
17. `test_upsert_no_overwrite_dict_enabled` must cover all three SSK importers.
18. Update `README.md` in the same commit as any change in the README Maintenance table.
19. All commit messages follow Conventional Commits (`feat:`, `fix:`, `schema:`, `chore:`, `docs:`, `test:`, `refactor:`).
