# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Sub-directory CLAUDE.md files** (loaded automatically when working in those directories):
- `supabase/CLAUDE.md` — Database schema, Pydantic models, UPSERT/Export RPC SQL
- `mozc4med_dict/CLAUDE.md` — Importer/Exporter specification, kana.py, download.py
- `tests/CLAUDE.md` — Unit and integration test guide
- `.github/CLAUDE.md` — GitHub Actions workflow definitions

## Development Commands

```bash
# Setup (first time)
python -m venv venv && source venv/bin/activate   # Linux/macOS
pip install -e ".[dev]"

# Lint & type check
ruff check . --fix
mypy mozc4med_dict/

# Tests
pytest tests/unit/ -v                              # unit tests (no network)
pytest tests/integration/ -v                       # requires SUPABASE_TEST_* env vars
pytest tests/unit/test_kana.py -v                  # single test file
pytest tests/unit/test_kana.py::test_normalize_hiragana -v  # single test case
pytest -v                                          # all tests
```

Copy `.env.example` to `.env` and fill in `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` before running scripts locally.

---

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

**SSK distribution format**: ZIP archive containing a single CSV file.
Filename convention: `s_ALL{YYYYMMDD}.csv` (shinryo_koi), `y_ALL{YYYYMMDD}.csv` (iyakuhin), `b_ALL{YYYYMMDD}.csv` (shobyomei).

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

Register all four secrets in **Settings → Secrets and variables → Actions**:

| Secret | Purpose |
|---|---|
| `SUPABASE_URL` | Production project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Full read/write access (production) |
| `SUPABASE_TEST_URL` | Dedicated test project URL |
| `SUPABASE_TEST_SERVICE_ROLE_KEY` | Full read/write access (test) |

> ⚠️ `SERVICE_ROLE_KEY` bypasses RLS. Never expose it in logs or `run:` step output.

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

## CLI Reference

```bash
# Import SSK masters (from https:// ZIP — primary usage)
python scripts/import_shinryo_koi.py --url "https://www.ssk.or.jp/.../s_ALL20260401.zip"
python scripts/import_iyakuhin.py    --url "https://www.ssk.or.jp/.../y_ALL20260401.zip"
python scripts/import_shobyomei.py   --url "https://www.ssk.or.jp/.../b_ALL20260401.zip"

# Import SSK masters (from local ZIP via file://)
python scripts/import_shinryo_koi.py --url "file:///path/to/s_ALL20260401.zip"
python scripts/import_iyakuhin.py    --url "file:///C:/Users/me/data/y_ALL20260401.zip"

# Import SSK masters (from local CSV directly via file://)
python scripts/import_shobyomei.py   --url "file:///path/to/b_ALL20260401.csv"

# Import custom terms
python scripts/import_csv.py         --file data/custom_terms.csv  --source "Custom terms v1"

# Export
python scripts/export_mozc_dict.py --output dist/mozc4med_medical.txt
python scripts/export_mozc_dict.py --dry-run    # Count only, no file written
gh workflow run export_mozc_dict.yml             # Trigger GHA manually

# Manage dict_enabled
python scripts/manage_dict_enabled.py --list-abolished
python scripts/manage_dict_enabled.py --disable 1234567             # 7桁 → ssk_shobyomei
python scripts/manage_dict_enabled.py --disable 123456789 --table shinryo_koi
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

## README.md Maintenance

**Update in the same commit** when any of the following change:

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

| Prefix | Group |
|---|---|
| `feat:` | Features |
| `fix:` | Bug Fixes |
| `schema:` | Schema Changes |
| `chore:` | Chores |
| `docs:` | Documentation |
| `test:` | Tests |
| `refactor:` | Refactor |

---

## Cross-Platform Compatibility

All code must run on **Windows, macOS, and Linux** without modification.

- **Paths**: always `pathlib.Path` — never string concatenation with `/` or `\`
- **File encoding**: always specify `encoding=` explicitly
  - SSK CSV input: `encoding="cp932"`
  - Dictionary output: `encoding="utf-8", newline="\n"` (force LF)
- **CLI scripts**: `argparse` only — no shell syntax (`&&`, `export`, backticks)
- **file:// URLs**: use `Path.as_uri()` for construction; `_url_to_local_path()` in `download.py` handles POSIX and Windows drive-letter paths

---

## Development Rules & Instructions for Claude Code

**Invariants** (never violate):

1. **Import-time: CP932 → UTF-8 only.** `normalize_reading()` is called only in `mozc_system_dict.py`.
2. **UPSERT via `client.rpc()` only.** `.upsert()` overwrites all columns; the Postgres RPC protects `dict_enabled`.
3. **`dict_enabled` は `DO UPDATE SET` に含めない。** Python 側でも設定しない。新規レコードへの `TRUE` 設定は RPC が行う。
4. **Soft-delete only.** Use `dict_enabled=FALSE` to exclude. Never `DELETE` rows from SSK tables.
5. **Credentials from `os.environ["KEY"]` only.** Never hardcode; never `os.getenv`.
6. **SHA-256 dedup** is handled by `BaseImporter._abort_if_duplicate()` — never re-implement. SHA-256 is computed on the **CSV file** (after ZIP extraction), not on the ZIP archive.
7. **URL resolution is script-layer only.** `resolve_csv()` is called in `scripts/import_*.py`, never inside `BaseImporter` or its subclasses. `BaseImporter.run()` always receives a local `Path`.

**Implementation rules**:

8. All SSK importers subclass `BaseImporter` and implement only `_parse()`. Never re-implement `run()`, `_upsert()`, `_sha256()`, `_create_batch()` in a subclass.
9. `custom_terms` の `reading` はインポート時に平仮名であることを前提とし、`normalize_reading()` を通さない。
10. SSK fields: `row[field_no - 1]` (0-indexed; field numbers from SSK PDF spec).
11. POS IDs: populate `pos_types` from `src/data/dictionary_oss/id.def`; export RPC looks up by `category` at runtime.
12. Migrations: timestamp-prefixed SQL in `supabase/migrations/`; apply to test project on every addition.
13. **Cross-platform**: `pathlib.Path`; explicit `encoding=`; `newline="\n"` for output files; `_url_to_local_path()` for `file://` URI parsing.

**Process rules**:

14. `load_dotenv()` once only, at top of `db.py`.
15. In GHA workflows, secrets via `env:` only — never `${{ secrets.* }}` inside `run:`.
16. Raise exceptions in library code; log and handle at the script layer.
17. Run `pytest tests/unit/` before touching integration tests (no network in unit tests; mock `db.get_client()` and `urlopen`).
18. `test_upsert_no_overwrite_dict_enabled` must cover all three SSK importers.
19. Update `README.md` in the same commit as any change in the README Maintenance table.
20. All commit messages follow Conventional Commits (`feat:`, `fix:`, `schema:`, `chore:`, `docs:`, `test:`, `refactor:`).
