# Copilot Instructions (Mozc4med)

## Scope and source of truth

- This repository manages Japanese medical terms in Supabase and exports a Mozc system dictionary TSV.
- Treat the CLAUDE.md files as the authoritative project policy:
  - `/CLAUDE.md`
  - `/mozc4med_dict/CLAUDE.md`
  - `/supabase/CLAUDE.md`
  - `/tests/CLAUDE.md`
  - `/.github/CLAUDE.md`

## Non-negotiable invariants

1. Importers perform CP932 -> UTF-8 conversion only. Do not normalize kana during import.
2. `normalize_reading()` is called only in `mozc4med_dict/exporters/mozc_system_dict.py`.
3. Always use `get_client()` from `mozc4med_dict/db.py`; do not instantiate Supabase clients directly.
4. Read credentials only via `os.environ["KEY"]`; never use `os.getenv`.
5. For SSK writes, use Postgres RPC (`client.rpc("upsert_*", ...)`) only; do not use `.upsert()`.
6. Never overwrite `dict_enabled` on re-import (`DO UPDATE SET` must not include it).
7. Use soft exclusion only (`dict_enabled = FALSE`); never hard-delete SSK records.
8. URL resolution belongs to script layer (`resolve_csv()` in `scripts/import_*.py`); `BaseImporter.run()` always takes a local `Path`.
9. All SSK importers must subclass `BaseImporter` and implement only `_parse()`.
10. Duplicate detection must rely on `BaseImporter._abort_if_duplicate()`, using SHA-256 of extracted CSV (not ZIP).

## Data model behavior

- `is_active` (SSK lifecycle) and `dict_enabled` (dictionary inclusion) are independent flags.
- Export filters by `dict_enabled` only; never by `is_active`.
- `custom_terms.reading` is assumed to be valid hiragana at import; do not pass it through `normalize_reading()`.

## Cross-platform and I/O

- Use `pathlib.Path` for all path handling.
- Always set encoding explicitly:
  - SSK CSV input: `encoding="cp932"`
  - Dictionary output: `encoding="utf-8", newline="\n"`
- Keep CLI scripts `argparse`-based and shell-agnostic.
- For `file://` handling, use `Path.as_uri()` for generation and existing `_url_to_local_path()` logic for parsing.

## Testing expectations

- Run unit tests first: `pytest tests/unit/ -v`.
- Unit tests must not use network; mock `db.get_client()` and `urllib.request.urlopen` where needed.
- Integration tests require `SUPABASE_TEST_*` and must target the test project only.
- `test_upsert_no_overwrite_dict_enabled` must cover all three SSK importers.

## GitHub Actions expectations

- Inject secrets via `env:` only.
- Never interpolate `${{ secrets.* }}` directly inside `run:`.
- Preserve workflow intent:
  - `ci.yml`: lint, unit tests, integration tests
  - `export_mozc_dict.yml`: scheduled/manual export and auto-commit
  - `import_ssk_master.yml`: manual SSK import
  - `supabase_keepalive.yml`: read-only keepalive query
  - `update_changelog.yml`: regenerate CHANGELOG via git-cliff

## Documentation and commits

- If changing CLI flags, schema, workflows, dependencies, cost/POS mapping, or reading-normalization policy, update `README.md` in the same commit.
- Keep required README sections complete: requirements, setup, importing, exporting, dict management, tests, schema, workflows, license.
- Use Conventional Commits prefixes: `feat:`, `fix:`, `schema:`, `chore:`, `docs:`, `test:`, `refactor:`.
