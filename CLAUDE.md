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

**Common file specification (SSK masters)**:
- Encoding: Shift-JIS (cp932)
- Field delimiter: `,` (comma)
- Numeric fields: leading zeros omitted
- Download page: https://www.ssk.or.jp/seikyushiharai/tensuhyo/kihonmasta/

### Output Format — Mozc System Dictionary

```
reading\tleft_id\tright_id\tcost\tsurface_form
```

| Field | Description | Example |
|---|---|---|
| `reading` | Hiragana pronunciation | `とうにょうびょう` |
| `left_id` | Left context POS ID (from Mozc `id.def`) | `1849` |
| `right_id` | Right context POS ID (from Mozc `id.def`) | `1849` |
| `cost` | Generation cost (0–10000; lower = higher priority) | `4800` |
| `surface_form` | Display form | `糖尿病` |

---

## Directory Structure

```
mozc4med-dict/
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── .env.example             # Template for local dev (no secrets)
├── .env                     # Local secrets — gitignored
├── .github/
│   └── workflows/
│       ├── export_mozc_dict.yml    # Dictionary export (main)
│       ├── import_ssk_master.yml   # SSK master import (manual trigger)
│       ├── supabase_keepalive.yml  # Prevent Supabase free-tier freeze (daily ping)
│       ├── ci.yml                  # CI: lint + unit tests + integration tests (on PR)
│       └── update_changelog.yml    # Regenerate CHANGELOG.md via git-cliff (on push to main)
├── cliff.toml                  # git-cliff configuration for CHANGELOG generation
├── dist/
│   └── mozc4med_medical.txt        # Exported dictionary (committed back by GHA)
├── supabase/
│   └── migrations/
│       ├── 20260101000001_create_pos_types.sql
│       ├── 20260101000002_create_import_batches.sql
│       ├── 20260101000003_create_ssk_shinryo_koi.sql
│       ├── 20260101000004_create_ssk_iyakuhin.sql
│       ├── 20260101000005_create_ssk_shobyomei.sql
│       ├── 20260101000006_create_custom_terms.sql
│       └── 20260101000007_create_export_rpc.sql
├── mozc4med_dict/
│   ├── __init__.py
│   ├── db.py                       # Supabase client (reads from env vars)
│   ├── models.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── kana.py                 # Katakana → hiragana conversion (export-time only)
│   ├── importers/
│   │   ├── __init__.py
│   │   ├── base.py                 # Base importer (batch registration logic)
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
│   ├── manage_dict_enabled.py      # Inspect / toggle dict_enabled flags
│   └── supabase_keepalive.py       # Supabase freeze-prevention ping
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

---

## Credentials & Secrets Management

### Principle

| Environment | Source | How to configure |
|---|---|---|
| Local development | `.env` file | Copy `.env.example` and fill in values |
| GitHub Actions | `secrets.*` | Register in repository Settings → Secrets |

`db.get_client()` always reads credentials from **environment variables**.
On local, `python-dotenv` loads `.env` automatically.
On GitHub Actions, secrets are injected as env vars directly — no `.env` needed.

### Required GitHub Secrets

Register in **Settings → Secrets and variables → Actions**.

| Secret | Value | Purpose |
|---|---|---|
| `SUPABASE_URL` | `https://xxxx.supabase.co` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | `eyJ...` | Full read access for export/import |

### Python library: `supabase-py`

All Supabase operations use **[supabase-py](https://github.com/supabase-community/supabase-py)**,
the official Python client for Supabase.

```toml
# pyproject.toml
[project]
dependencies = [
    "supabase>=2.0",        # supabase-py — Supabase Python client
    "python-dotenv>=1.0",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-mock",          # Mock supabase-py client in unit tests
    "ruff",
    "mypy",
]
```

Key APIs used in this project:

```python
from supabase import create_client, Client

client = create_client(url, key)

# SELECT
client.table("ssk_shobyomei").select("*").eq("dict_enabled", True).execute()

# UPSERT (on_conflict targets the UNIQUE constraint column)
client.table("ssk_shobyomei").upsert(records, on_conflict="shobyomei_code").execute()

# UPDATE
client.table("import_batches").update({"record_count": n}).eq("id", batch_id).execute()
```

> Use `supabase-py` for all DB operations — do not use `psycopg2` or raw SQL strings
> unless a query is too complex for the supabase-py query builder (e.g. multi-table UNION).
> In that case, use `client.rpc()` to call a Postgres function defined in Supabase.

> ⚠️ `SERVICE_ROLE_KEY` bypasses RLS and has full data access.
> Never expose it in logs, artifacts, or `run:` step output.

### `.env.example`
```dotenv
# For local development only. Safe to commit.
# Copy to .env and fill in real values (.env is gitignored).
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

### `mozc4med_dict/db.py` Implementation

Uses **supabase-py** (`supabase.create_client`). Do not use psycopg2 or raw connections.

```python
import os
from supabase import create_client, Client  # supabase-py
from dotenv import load_dotenv

# Load .env for local runs. On GHA, env vars are already injected.
load_dotenv()

def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]               # KeyError immediately if not set
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)
```

Use `os.environ["KEY"]` (not `os.getenv`) so that missing secrets cause an immediate,
clear `KeyError` rather than a cryptic failure deep in the Supabase client.

---

## Database Schema

### Design Principle: Two-Flag Separation

SSK master "abolition" and Mozc dictionary "exclusion" are **independent concerns**
managed by separate flags.

| Flag | Meaning | Changed by |
|---|---|---|
| `is_active` | Term is still current in the SSK master | Importer (automatic) |
| `dict_enabled` | Term should be included in the Mozc dictionary | Admin (manual) |

```
An abolished term (is_active=FALSE) remains in the dictionary as long as dict_enabled=TRUE.
A term is removed from the dictionary only when an admin explicitly sets dict_enabled=FALSE.
```

**The exporter filters on `dict_enabled` only — `is_active` is ignored**:
```sql
WHERE dict_enabled = TRUE
```

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

> ⚠️ Verify actual IDs against `src/data/dictionary_oss/id.def` in the Mozc4med repository.

---

### `import_batches` — Import history

All records in a single SSK master CSV share the same source URL and file.
Provenance is therefore tracked at **batch level**, not per-record.
This eliminates redundancy and ensures reproducibility for academic papers
(Methods section can cite exact file version and SHA-256 hash).

```sql
CREATE TABLE import_batches (
    id            BIGSERIAL PRIMARY KEY,
    source_type   TEXT        NOT NULL,
    -- 'ssk_shinryo_koi' | 'ssk_iyakuhin' | 'ssk_shobyomei' | 'custom_csv'
    source_url    TEXT,
    -- Download page URL
    -- e.g. https://www.ssk.or.jp/seikyushiharai/tensuhyo/kihonmasta/kihonmasta_07.html
    file_name     TEXT        NOT NULL,  -- e.g. b_ALL20260325.csv
    file_sha256   TEXT,                  -- SHA-256 of the raw file (reproducibility + dedup)
    record_count  INTEGER,               -- Number of records actually imported
    imported_by   TEXT,                  -- Username or 'github-actions'
    imported_at   TIMESTAMPTZ DEFAULT NOW(),
    notes         TEXT
);
```

**`file_sha256` uses**:
- Prevent re-importing the same file (check hash before import)
- Academic citation: "We used the version dated 2026-03-25 (SHA-256: xxxx)"

---

### `ssk_shinryo_koi` — Medical procedure master

Field mapping (field numbers match the SSK PDF spec; 0-indexed access = `row[field_no - 1]`):

| Field no. | Japanese name | Width | Column |
|-----------|--------------|-------|--------|
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
    shinryo_koi_code    TEXT    NOT NULL UNIQUE,  -- 9-digit procedure code
    abbr_kanji_name     TEXT,                     -- Abbreviated kanji name (used as surface_form)
    abbr_kana_name      TEXT,                     -- Abbreviated kana name (stored as-is; normalized at export)
    base_kanji_name     TEXT,                     -- Full kanji name (fallback for surface_form)
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

**Dictionary conversion**: `surface_form` → `abbr_kanji_name` → fallback `base_kanji_name` / `cost` = 5500

---

### `ssk_iyakuhin` — Drug master

| Field no. | Japanese name | Width | Column |
|-----------|--------------|-------|--------|
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
    iyakuhin_code       TEXT    NOT NULL UNIQUE,  -- 9-digit drug code
    kanji_name          TEXT,                     -- Brand name (surface_form)
    kana_name           TEXT,                     -- Kana name (stored as-is; normalized at export)
    base_kanji_name     TEXT,
    generic_name_code   TEXT,
    generic_name_label  TEXT,                     -- INN / standard generic prescription label
    is_generic          BOOLEAN,                  -- TRUE = generic (後発品)
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

**Dictionary conversion**: generates **two entries** per record — `kanji_name` (brand name) and `generic_name_label` (INN label).
`cost`: originator = 5000, generic (`is_generic=TRUE`) = 5200.

---

### `ssk_shobyomei` — Disease / injury name master

| Field no. | Japanese name | Width | Column |
|-----------|--------------|-------|--------|
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
    shobyomei_code      TEXT    NOT NULL UNIQUE,  -- 7-digit disease code
    successor_code      TEXT,                     -- Successor code when abolished
    base_name           TEXT,                     -- Full disease name (surface_form)
    abbr_name           TEXT,                     -- Abbreviated name (fallback)
    kana_name           TEXT,                     -- Kana name (stored as-is; normalized at export)
    byomei_mgmt_code    TEXT,                     -- MEDIS-DC linkage key
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

**Dictionary conversion**: `surface_form` → `base_name` → fallback `abbr_name` / `cost` = 4800 (highest priority)

---

### `custom_terms` — Manual / CSV terms

Custom terms can have per-record provenance (different URLs, spreadsheets, etc.),
so `source_url` is stored directly on the record rather than via `import_batches`.
`custom_terms` has no `is_active` flag — abolition is not a concept for custom entries.

```sql
CREATE TABLE custom_terms (
    id              BIGSERIAL PRIMARY KEY,
    surface_form    TEXT    NOT NULL,
    reading         TEXT    NOT NULL,       -- Hiragana only
    pos_type_id     INTEGER REFERENCES pos_types(id),
    cost            INTEGER NOT NULL DEFAULT 5000,
    source_label    TEXT,                   -- e.g. 'Custom terms v1'
    source_url      TEXT,                   -- Origin URL (optional)
    notes           TEXT,
    dict_enabled    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (surface_form, reading)
);
```

---

## Importer Specification

### Character Encoding Policy

**Import-time conversion: UTF-8 only. All other normalizations are deferred to export.**

| Phase | What happens | What does NOT happen |
|---|---|---|
| **Import** | CP932 → UTF-8 conversion only | No kana normalization, no case folding |
| **Export** | `normalize_reading()` converts DB value → hiragana | — |

**Rationale**: SSK master kana fields contain mixed content in practice.
Confirmed real-world examples:

| Term | Kana field value | Content |
|---|---|---|
| 医療DX | `ｲﾘｮｳDX` | Half-width kana + ASCII uppercase |
| 1型糖尿病 | `1ｶﾞﾀﾄｳﾆｮｳﾋﾞｮｳ` | ASCII digit + half-width dakuten kana |

Storing the raw SSK value in the DB:
- Preserves the original data for audit and academic citation
- Avoids irreversible transformation at import time
- Allows `normalize_reading()` logic to be improved without re-importing

> **Column comment convention**: kana columns in SSK tables carry the comment
> `"stored as-is (CP932→UTF-8 only); normalized to hiragana at export via normalize_reading()"`.

---

### Batch Registration Flow (`importers/base.py`)

All SSK importers must inherit from the base importer, which handles:

```
1. Compute SHA-256 of the input file
2. Check import_batches for an existing row with the same file_sha256
   → If found: abort with a clear error (duplicate import prevention)
3. INSERT a new row into import_batches, capture batch_id
4. UPSERT each record (see rules below)
5. UPDATE import_batches.record_count with the actual count
```

### `change_type` Handling Rules (all SSK masters)

| change_type | is_active | dict_enabled | Note |
|---|---|---|---|
| `1` (new) | TRUE | TRUE | Both flags ON |
| `3` (modified) | TRUE | **do not touch** | Respect admin intent |
| `4` (abolished) | FALSE | **do not touch** | Term stays in dictionary |

### UPSERT Pattern — never update `dict_enabled`

```sql
INSERT INTO ssk_shobyomei (
    shobyomei_code, base_name, kana_name, ..., is_active, dict_enabled, batch_id
)
VALUES (%s, %s, %s, ..., %s, TRUE, %s)
ON CONFLICT (shobyomei_code) DO UPDATE SET
    base_name    = EXCLUDED.base_name,
    kana_name    = EXCLUDED.kana_name,
    abolished_at = EXCLUDED.abolished_at,
    is_active    = EXCLUDED.is_active,
    batch_id     = EXCLUDED.batch_id,
    imported_at  = NOW()
    -- dict_enabled intentionally omitted
;
```

---

## Exporter Specification (`exporters/mozc_system_dict.py`)

```sql
-- All four tables: filter on dict_enabled only; is_active is irrelevant
SELECT ... FROM ssk_shobyomei   WHERE dict_enabled = TRUE
UNION ALL
SELECT ... FROM ssk_iyakuhin    WHERE dict_enabled = TRUE
UNION ALL
SELECT ... FROM ssk_shinryo_koi WHERE dict_enabled = TRUE
UNION ALL
SELECT ... FROM custom_terms    WHERE dict_enabled = TRUE
```

### Cost table

| Table | cost | Note |
|---|---|---|
| ssk_shobyomei | 4800 | Highest priority |
| ssk_iyakuhin (originator) | 5000 | |
| ssk_iyakuhin (generic) | 5200 | |
| ssk_shinryo_koi | 5500 | |
| custom_terms | per-row value | Default 5000 |

---

## `utils/kana.py` — `normalize_reading()` Specification

`normalize_reading()` is called **only at export time**, never at import time.
It converts a raw kana field value (as stored in the DB) to a valid Mozc `reading`
(hiragana only).

### Conversion pipeline

```
Input (raw DB value)
  │
  ├─ 1. 全角カタカナ → 平仮名       unicodedata / str.translate
  ├─ 2. 半角カナ（濁点合成含む）→ 全角カタカナ → 平仮名
  │       例: ｶﾞ→ガ→が、ｲﾘｮｳ→イリョウ→いりょう
  │
  ├─ 3. 残留文字の処理（上記変換後も平仮名以外が残る場合）
  │
  │   ASCII 英字（例: DX, CT, MRI）
  │     → WARNING ログ出力 + その TSV 行をスキップ（辞書に出力しない）
  │     → 対象レコードに dict_enabled=FALSE は設定しない（DB は変更しない）
  │
  │   ASCII 数字（例: 1型糖尿病の "1"）
  │     → WARNING ログ出力 + その TSV 行をスキップ
  │     （Mozc の reading フィールドは平仮名のみ有効）
  │
  │   その他の非平仮名文字（記号・漢字等）
  │     → ValueError を送出（呼び出し元でログ記録・スキップ）
  │
  └─ Output: 平仮名のみの文字列 or スキップ（TSV 未出力）
```

> **スキップ vs. ValueError の使い分け**
> - 英字・数字残留: エクスポーターが WARNING ログを出して行をスキップ（`normalize_reading()` は値を返さず `None` を返す、またはエクスポーター側でフィルタ）
> - 予期しない文字種: `ValueError` を送出して呼び出し元に委ねる

### スキップされたエントリのログ形式

```
WARNING: skipped reading normalization: table=ssk_shobyomei code=XXXXXXX
         raw_kana='ｲﾘｮｳDX' reason='residual_ascii_alpha'
WARNING: skipped reading normalization: table=ssk_shobyomei code=XXXXXXX
         raw_kana='1ｶﾞﾀﾄｳﾆｮｳﾋﾞｮｳ' reason='residual_ascii_digit'
```

スキップされたエントリ数はエクスポートスクリプトの終了時にサマリーとして出力する:

```
INFO: export complete: 42381 entries written, 17 entries skipped (see WARNING logs)
```

### Unit test cases for `kana.py`

| Input | Expected output | Notes |
|---|---|---|
| `イリョウ` | `いりょう` | 全角カタカナ |
| `ｲﾘｮｳ` | `いりょう` | 半角カナ |
| `ｶﾞﾀ` | `がた` | 半角濁点合成 |
| `1ｶﾞﾀﾄｳﾆｮｳﾋﾞｮｳ` | `None` (skip) | 数字残留（実確認例） |
| `ｲﾘｮｳDX` | `None` (skip) | ASCII英字残留（実確認例） |
| `漢字` | `ValueError` | 非カナ文字 |
| `` (empty) | `ValueError` | 空文字列 |

---

## GitHub Actions Workflows

### Overview

| Workflow file | Trigger | Purpose |
|---|---|---|
| `export_mozc_dict.yml` | schedule (weekly) + `workflow_dispatch` | Export dictionary and commit back |
| `import_ssk_master.yml` | `workflow_dispatch` only | Import SSK master CSV |
| `supabase_keepalive.yml` | schedule (daily) | Prevent Supabase free-tier freeze |

Supabase credentials are **always passed via `env:` from `secrets.*`**.
Never interpolate `${{ secrets.* }}` directly inside a `run:` step (risk of log exposure).

```yaml
# Correct pattern for all workflows
- name: Run script
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
  run: python scripts/some_script.py
```

---

### `export_mozc_dict.yml`

```yaml
name: Export Mozc Dictionary

on:
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * 1'    # Every Monday 02:00 UTC (JST 11:00)

jobs:
  export:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e .

      - name: Export Mozc dictionary
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
        run: |
          python scripts/export_mozc_dict.py \
            --output dist/mozc4med_medical.txt

      - name: Commit and push
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add dist/mozc4med_medical.txt
          git diff --cached --quiet || git commit -m "chore: update mozc4med_medical.txt"
          git push
```

---

### `supabase_keepalive.yml`

Supabase free-tier projects are paused after a period of inactivity.
A lightweight daily SELECT keeps the project active.

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
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e .

      - name: Ping Supabase
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
        run: python scripts/supabase_keepalive.py
```

**`scripts/supabase_keepalive.py`**:

```python
"""
Supabase freeze-prevention script.
Runs a minimal SELECT against import_batches — no writes.
import_batches is chosen because it is the lightest table
and returns no error when empty.
"""
import logging
from mozc4med_dict.db import get_client

logging.basicConfig(level=logging.INFO)

client = get_client()
client.table("import_batches").select("id").limit(1).execute()
logging.info("keep-alive OK: Supabase is reachable")
```

---

### `import_ssk_master.yml`

SSK master updates are irregular, so this workflow is **manual-trigger only**.

```yaml
name: Import SSK Master

on:
  workflow_dispatch:
    inputs:
      master_type:
        description: 'Master type to import'
        required: true
        type: choice
        options:
          - shinryo_koi
          - iyakuhin
          - shobyomei
      file_url:
        description: 'Direct URL to the full CSV file (from SSK ZIP)'
        required: true
        type: string

jobs:
  import:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e .

      - name: Download master CSV
        run: curl -fsSL "${{ inputs.file_url }}" -o master.csv

      - name: Import master
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
        run: |
          python scripts/import_${{ inputs.master_type }}.py \
            --file master.csv \
            --url "${{ inputs.file_url }}" \
            --imported-by "github-actions"
```

---

## CLI Reference

```bash
# Import SSK masters (local run; credentials from .env)
python scripts/import_shinryo_koi.py \
  --file data/s_ALL20260325.csv \
  --url "https://www.ssk.or.jp/.../kihonmasta_01.html"

python scripts/import_iyakuhin.py \
  --file data/y_ALL20260325.csv \
  --url "https://www.ssk.or.jp/.../kihonmasta_04.html"

python scripts/import_shobyomei.py \
  --file data/b_ALL20260325.csv \
  --url "https://www.ssk.or.jp/.../kihonmasta_07.html"

python scripts/import_csv.py \
  --file data/custom_terms.csv \
  --source "Custom terms v1"

# Export Mozc dictionary
python scripts/export_mozc_dict.py --output dist/mozc4med_medical.txt
python scripts/export_mozc_dict.py --dry-run    # Count only, no file written

# Trigger export workflow manually
gh workflow run export_mozc_dict.yml

# Manage dict_enabled flags
python scripts/manage_dict_enabled.py --list-abolished    # List abolished terms still in dict
python scripts/manage_dict_enabled.py --disable <code>    # Remove term from dictionary
```

---

## Verification & Testing

### Overview

| Layer | Tool | When |
|---|---|---|
| Static analysis | `ruff check` + `mypy` | On every file save / pre-commit |
| Unit tests | `pytest` | Local + CI on every push |
| Integration tests | `pytest` + dedicated Supabase test project | Local + CI on every PR |
| CI pipeline | GitHub Actions `ci.yml` | Triggered on pull requests to `main` |

---

### Additional GitHub Secrets (test project)

Register alongside the production secrets in **Settings → Secrets and variables → Actions**.

| Secret | Value | Purpose |
|---|---|---|
| `SUPABASE_TEST_URL` | `https://yyyy.supabase.co` | Dedicated test project URL |
| `SUPABASE_TEST_SERVICE_ROLE_KEY` | `eyJ...` | Test project service role key |

The test project schema must be kept in sync with `supabase/migrations/`.
Run all migrations against the test project whenever a new migration is added.

---

### Static Analysis

```bash
# Lint + auto-fix
ruff check . --fix

# Type checking
mypy mozc4med_dict/
```

`pyproject.toml` configuration:

```toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]   # pycodestyle, pyflakes, isort, pyupgrade

[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true
```

---

### Unit Tests (`tests/unit/`)

Unit tests must run **without any network access** — no Supabase connection, no file I/O.
Use `pytest` with `unittest.mock` or `pytest-mock` to stub out `db.get_client()`.

```
tests/
├── unit/
│   ├── test_kana.py            # normalize_reading() edge cases (see table above)
│   ├── test_importer_base.py   # SHA-256 dedup logic, change_type routing
│   ├── test_ssk_shobyomei.py   # Field mapping (field_no → column)
│   ├── test_ssk_iyakuhin.py    # Dual-entry generation (brand + INN)
│   ├── test_ssk_shinryo_koi.py
│   └── test_mozc_exporter.py   # TSV line format, cost values, skip-count logging
└── integration/
    └── ...                     # see below
```

Key cases to cover in unit tests:

| Module | What to test |
|---|---|
| `utils/kana.py` | 全角カタカナ、半角カナ（濁点合成含む）、`ｲﾘｮｳDX`→`None`、`1ｶﾞﾀ...`→`None`、漢字→`ValueError` |
| `importers/base.py` | Duplicate SHA-256 aborts; `change_type=4` sets `is_active=False`; `dict_enabled` not touched on update |
| `exporters/mozc_system_dict.py` | TSV format (`\t` delimited, 5 fields); correct cost per table; UTF-8 LF output; skipped entries logged with count |

```bash
# Run unit tests only
pytest tests/unit/ -v
```

---

### Integration Tests (`tests/integration/`)

Integration tests run against the **dedicated Supabase test project**.
Credentials are loaded from environment variables (same mechanism as production).

```
tests/
└── integration/
    ├── conftest.py              # Session-scoped client; truncate tables before each test
    ├── test_import_shobyomei.py # Full CSV → DB round-trip
    ├── test_import_iyakuhin.py
    ├── test_import_shinryo_koi.py
    ├── test_upsert_no_overwrite_dict_enabled.py  # CRITICAL: dict_enabled must survive re-import
    ├── test_sha256_dedup.py     # Same file imported twice → second run aborts
    └── test_export_pipeline.py  # DB → TSV output validation (including skip-count)
```

`tests/integration/conftest.py` pattern:

```python
import os
import pytest
from supabase import create_client, Client

@pytest.fixture(scope="session")
def client() -> Client:
    url = os.environ["SUPABASE_TEST_URL"]
    key = os.environ["SUPABASE_TEST_SERVICE_ROLE_KEY"]
    return create_client(url, key)

@pytest.fixture(autouse=True)
def truncate_tables(client: Client):
    """Wipe all test data before each test for isolation."""
    for table in ["ssk_shobyomei", "ssk_iyakuhin", "ssk_shinryo_koi",
                  "custom_terms", "import_batches"]:
        client.table(table).delete().neq("id", 0).execute()
```

**Must-have integration test — `dict_enabled` survives re-import**:

```python
def test_upsert_does_not_overwrite_dict_enabled(client):
    # 1. Import a record
    import_shobyomei(client, [sample_row], batch_id=1)
    # 2. Manually disable it
    client.table("ssk_shobyomei") \
        .update({"dict_enabled": False}) \
        .eq("shobyomei_code", sample_row.code).execute()
    # 3. Re-import the same record (simulates a master update)
    import_shobyomei(client, [sample_row], batch_id=2)
    # 4. dict_enabled must still be False
    row = client.table("ssk_shobyomei") \
        .select("dict_enabled") \
        .eq("shobyomei_code", sample_row.code) \
        .single().execute().data
    assert row["dict_enabled"] is False
```

```bash
# Run integration tests (requires SUPABASE_TEST_* env vars)
pytest tests/integration/ -v

# Run all tests
pytest -v
```

---

### CI Workflow — `ci.yml`

Runs on every pull request to `main`. Blocks merge if any check fails.

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
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: mypy mozc4med_dict/

  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: pytest tests/unit/ -v

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests         # Run only after unit tests pass
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - name: Run integration tests
        env:
          SUPABASE_TEST_URL: ${{ secrets.SUPABASE_TEST_URL }}
          SUPABASE_TEST_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_TEST_SERVICE_ROLE_KEY }}
        run: pytest tests/integration/ -v
```

The three jobs run as: `lint` → `unit-tests` → `integration-tests`.
Integration tests are gated on unit tests passing to avoid burning Supabase API quota
on obviously broken code.

---

## README.md

### Generation & Maintenance

Claude Code generates `README.md` when the project is first initialized,
and **must update it whenever code changes affect usage, CLI arguments, or schema**.

### Required Sections

```markdown
# mozc4med-dict

One-line description of the project.

## Requirements
- Python 3.11+
- Supabase project (production + test)
- Access to SSK master CSV files

## Setup
1. Clone the repository
2. Copy `.env.example` to `.env` and fill in credentials
3. Install dependencies: `pip install -e ".[dev]"`
4. Apply migrations to your Supabase project (see `supabase/migrations/`)

## Importing SSK Masters
<!-- CLI usage for each import script with all flags -->

## Exporting the Mozc Dictionary
<!-- CLI usage for export_mozc_dict.py -->
<!-- Note: entries with non-hiragana residual after normalization are skipped with WARNING log -->

## Managing dict_enabled
<!-- CLI usage for manage_dict_enabled.py -->

## Running Tests
<!-- pytest commands for unit and integration tests -->

## Database Schema
<!-- Brief description of each table and the two-flag design -->
<!-- Note: kana columns store raw SSK values (CP932→UTF-8 only); normalized at export -->

## GitHub Actions Workflows
<!-- Table of all workflows, triggers, and purpose -->

## License
```

### Update Rules for Claude Code

When modifying any of the following, README.md **must** be updated in the same commit:

| Change | README section to update |
|---|---|
| New / changed CLI flag | Importing / Exporting / Managing sections |
| New table or column | Database Schema section |
| New workflow or changed trigger | GitHub Actions Workflows section |
| New dependency | Requirements / Setup sections |
| Changed cost values or POS mapping | Database Schema section |
| Changed normalize_reading() skip policy | Exporting section |

---

## CHANGELOG.md

### Tooling: `git-cliff` + Conventional Commits

`CHANGELOG.md` is **auto-generated** by [git-cliff](https://github.com/orhun/git-cliff)
on every push to `main`, using commit messages that follow
[Conventional Commits](https://www.conventionalcommits.org/) format.

### Conventional Commit Prefixes Used in This Project

| Prefix | Meaning | Appears in CHANGELOG |
|---|---|---|
| `feat:` | New feature or importer/exporter | ★ Features |
| `fix:` | Bug fix | ★ Bug Fixes |
| `schema:` | Database migration added | ★ Schema Changes |
| `chore:` | Dictionary export, keep-alive, CI tweaks | ★ Chores |
| `docs:` | README or CHANGELOG update | ★ Documentation |
| `test:` | Test additions or fixes | ★ Tests |
| `refactor:` | Code restructure without behavior change | ★ Refactor |

Commit message examples:
```
feat: add ssk_iyakuhin importer with dual-entry generation
fix: normalize half-width katakana in kana.py
schema: add batch_id foreign key to ssk_shobyomei
chore: update mozc4med_medical.txt
docs: update README CLI reference for export script
test: add dict_enabled upsert invariant test
```

### `cliff.toml` (place in repository root)

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

### `update_changelog.yml` Workflow

Runs on every push to `main`. Regenerates `CHANGELOG.md` and commits it back.

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
        with:
          fetch-depth: 0       # git-cliff needs full history

      - name: Generate CHANGELOG.md
        uses: orhun/git-cliff-action@v3
        with:
          config: cliff.toml
          args: --verbose
        env:
          OUTPUT: CHANGELOG.md

      - name: Commit CHANGELOG.md
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add CHANGELOG.md
          git diff --cached --quiet || git commit -m "docs: update CHANGELOG.md [skip ci]"
          git push
```

> `[skip ci]` in the commit message prevents the CI workflow from re-triggering
> on the auto-generated commit.

### Workflow File Summary (updated)

| Workflow file | Trigger | Purpose |
|---|---|---|
| `ci.yml` | PR to `main` | Lint + unit tests + integration tests |
| `export_mozc_dict.yml` | schedule (weekly) + manual | Export dictionary, commit back |
| `import_ssk_master.yml` | manual only | Import SSK master CSV |
| `supabase_keepalive.yml` | schedule (daily) | Prevent Supabase free-tier freeze |
| `update_changelog.yml` | push to `main` | Regenerate CHANGELOG.md via git-cliff |

---

## Cross-Platform Compatibility

All code must run on **Windows, macOS, and Linux** without modification.

### Path Handling

Never use string concatenation or hardcoded `/` separators for file paths.
Always use `pathlib.Path`.

```python
# ✗ Wrong
output = "dist/" + filename

# ✓ Correct
from pathlib import Path
output = Path("dist") / filename
```

### Line Endings

The exported Mozc dictionary (`dist/mozc4med_medical.txt`) must always be **UTF-8, LF (`\n`)**.
Force LF explicitly when writing — do not rely on the OS default:

```python
with open(output_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(line)
```

Add a `.gitattributes` to prevent Git from converting line endings:

```gitattributes
# .gitattributes
dist/mozc4med_medical.txt  text eol=lf
*.py                        text eol=lf
*.sql                       text eol=lf
*.md                        text eol=lf
*.toml                      text eol=lf
*.yml                       text eol=lf
```

### File Encoding

SSK master CSVs are Shift-JIS. Always specify encoding explicitly — never rely on the OS default:

```python
# ✓ Always explicit
with open(csv_path, encoding="cp932") as f:
    ...
```

### CLI Scripts

All scripts use `argparse` (stdlib) — no Bash or shell scripts.
This ensures identical behavior across platforms.

```python
# scripts/import_shobyomei.py
import argparse
from pathlib import Path

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--url",  type=str,  required=True)
    parser.add_argument("--imported-by", type=str, default="local")
    args = parser.parse_args()
    ...
```

### Environment Variables

`python-dotenv` loads `.env` on all platforms. No platform-specific env var syntax
(`export` / `set`) should appear in documentation examples — use `.env` or `os.environ` instead.

### `pyproject.toml` Entry Points

Define CLI entry points in `pyproject.toml` so scripts are invokable
as `mozc4med-export` etc. on all platforms (avoids `python scripts/xxx.py` on Windows PATH issues):

```toml
[project.scripts]
mozc4med-import-shinryo-koi = "scripts.import_shinryo_koi:main"
mozc4med-import-iyakuhin    = "scripts.import_iyakuhin:main"
mozc4med-import-shobyomei   = "scripts.import_shobyomei:main"
mozc4med-import-csv         = "scripts.import_csv:main"
mozc4med-export             = "scripts.export_mozc_dict:main"
mozc4med-keepalive          = "scripts.supabase_keepalive:main"
```

---

## Development Rules

1. **All `reading` values must be hiragana.** Always pass through `utils/kana.normalize_reading()` **at export time**.
2. **Import-time encoding: UTF-8 conversion only.** Do not normalize kana, fold case, or strip characters at import. The DB stores the raw SSK value (CP932→UTF-8). Normalization is the exporter's responsibility.
3. **POS IDs must come from `id.def`.** Check `src/data/dictionary_oss/id.def` in the Mozc4med repo.
4. Soft-delete only: use `dict_enabled=FALSE` to exclude terms. Never hard-delete rows.
5. **Never include `dict_enabled` in the `ON CONFLICT DO UPDATE` clause of any UPSERT.**
6. Before importing, check `file_sha256` against `import_batches` to prevent duplicate imports.
7. **Never hardcode credentials.** Always read from `os.environ`.
8. Access SSK CSV fields as `row[field_no - 1]` (0-indexed, field numbers from the SSK PDF spec).
9. Migrations live in `supabase/migrations/` as timestamp-prefixed SQL files (e.g. `20260101000001_create_pos_types.sql`).
10. **Cross-platform**: use `pathlib.Path` for all paths, always specify `encoding=` explicitly, write output files with `newline="\n"`.
11. Never use shell-specific syntax (`&&`, `export`, backticks) in Python code or documentation examples.
12. **normalize_reading() skip policy**: if a kana field value contains residual ASCII alphabet or digits after half-width kana conversion, log a WARNING and skip that TSV line. Do not write an invalid reading to the dictionary. Do not set `dict_enabled=FALSE` in the DB (DB is not modified at export time).

---

## Instructions for Claude Code

- Follow the directory structure above before creating any new module.
- Always access Supabase through `db.get_client()` — never instantiate the client directly.
- Use **supabase-py** (`supabase.create_client`) for all DB operations. Do not use `psycopg2` or raw SQL strings. For queries too complex for the supabase-py builder (e.g. multi-table `UNION ALL`), use `client.rpc()` with a Postgres function.
- Call `load_dotenv()` **once**, at the top of `db.py` only.
- **Importers perform CP932→UTF-8 conversion only.** Do not call `normalize_reading()` in any importer. Kana normalization happens exclusively in the exporter.
- Always use `utils/kana.normalize_reading()` for kana conversion in the exporter — never inline it.
- All importers must inherit from `importers/base.py` (batch registration is handled there).
- **CRITICAL: Never add `dict_enabled` to the `ON CONFLICT DO UPDATE` SET clause.**
- In GHA workflows, always pass secrets via `env:` — never expand `${{ secrets.* }}` inside `run:`.
- Raise exceptions from library code; log and handle them at the script layer.
- Place unit tests under `tests/unit/` and integration tests under `tests/integration/`.
- Unit tests must not make any network calls — mock `db.get_client()` with `pytest-mock`.
- Integration tests must use `SUPABASE_TEST_URL` / `SUPABASE_TEST_SERVICE_ROLE_KEY`, never the production credentials.
- Always include `test_upsert_no_overwrite_dict_enabled` when implementing any importer.
- Ensure `pytest tests/unit/` passes before touching integration tests.
- **README.md must be updated in the same commit** whenever CLI flags, schema, workflows, or dependencies change. See the README.md section for which section to update.
- All commit messages must follow **Conventional Commits** format (`feat:`, `fix:`, `schema:`, `chore:`, `docs:`, `test:`, `refactor:`). This drives automatic CHANGELOG generation via git-cliff.
- **Always use `pathlib.Path`** for file paths — never string concatenation with `/` or `\`.
- **Always specify `encoding=`** when opening any file — never rely on the OS default.
- Output files must use `newline="\n"` (LF) regardless of the host OS.
- When implementing `normalize_reading()`: half-width kana → full-width kana → hiragana is the primary path. Residual ASCII alpha/digit after conversion → return `None` and log WARNING at the exporter layer. Unexpected characters (kanji, symbols) → raise `ValueError`.
