# .github/ — GitHub Actions Workflows

## Workflow Overview

| Workflow | Trigger | Purpose |
|---|---|---|
| `ci.yml` | PR to `main` | Lint → unit tests → integration tests |
| `export_mozc_dict.yml` | Weekly (Mon 02:00 UTC) + manual | Export dictionary, commit back |
| `import_ssk_master.yml` | Manual only | Import SSK master (ZIP download handled by script) |
| `supabase_keepalive.yml` | Daily (00:00 UTC) | Prevent free-tier freeze |
| `update_changelog.yml` | Push to `main` | Regenerate CHANGELOG.md via git-cliff |

**Secret injection rule**: always via `env:` — never interpolate `${{ secrets.* }}` inside `run:`.

```yaml
# Correct pattern for all workflows
- name: Run script
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
  run: python scripts/some_script.py
```

---

## `ci.yml`

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

## `export_mozc_dict.yml`

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

## `import_ssk_master.yml`

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
        description: 'URL to ZIP or CSV file (https:// or file://)'
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
      - name: Import
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
        run: |
          python scripts/import_${{ inputs.master_type }}.py \
            --url "${{ inputs.file_url }}" --imported-by "github-actions"
```

> Note: The script handles ZIP download and extraction internally via `resolve_csv()`.
> No separate `curl` step is needed.

## `supabase_keepalive.yml`

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

## `update_changelog.yml`

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
