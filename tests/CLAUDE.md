# tests/ — Testing Guide

## Commands

```bash
pytest tests/unit/ -v                              # unit tests (no network)
pytest tests/integration/ -v                       # requires SUPABASE_TEST_* env vars
pytest tests/unit/test_kana.py -v                  # single test file
pytest tests/unit/test_kana.py::test_normalize_hiragana -v  # single test case
pytest -v                                          # all tests
```

## Unit Tests (`tests/unit/`)

Unit tests must run with **no network access** — mock `db.get_client()` with `pytest-mock`.
For `utils/download.py`, mock `urllib.request.urlopen` for `https://` tests.

| Module | What to test |
|---|---|
| `utils/kana.py` | All cases in the normalize_reading() test table (see `mozc4med_dict/CLAUDE.md`) |
| `utils/download.py` | `file://` CSV direct; `file://` ZIP extract; `https://` download+extract (mock `urlopen`); glob no-match error; multiple CSV match error; invalid ZIP error; unsupported scheme error; Windows `file:///C:/` path parsing; URL-encoded paths |
| `importers/base.py` | `_sha256()` correctness; `_abort_if_duplicate()` raises on existing hash; `change_type=4` → `is_active=False`; `dict_enabled` absent from `_parse()` output |
| `exporters/mozc_system_dict.py` | TSV format (tab-delimited, 5 fields); correct cost per source; UTF-8 LF; `ValueError` rows skipped and counted |

## Integration Tests (`tests/integration/`)

Tests use `SUPABASE_TEST_*` credentials — never production.
Schema must be kept in sync with `supabase/migrations/` (apply every new migration to the test project).

`conftest.py` pattern:

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

`test_upsert_no_overwrite_dict_enabled` must cover **all three SSK importers**.
