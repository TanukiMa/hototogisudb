# mozc4med_dict/ — Importer & Exporter Specification

## Character Encoding Policy

**Import-time: CP932 → UTF-8 only. All kana normalization is deferred to export.**

SSK kana fields contain mixed content in practice. Confirmed real-world examples:

| Term | kana_name value | Content |
|---|---|---|
| 医療DX | `ｲﾘｮｳDX` | Half-width kana + ASCII uppercase |
| 1型糖尿病 | `1ｶﾞﾀﾄｳﾆｮｳﾋﾞｮｳ` | ASCII digit + half-width dakuten kana |

Storing raw values preserves original data for audit/citation and allows `normalize_reading()` to be improved without re-importing.

---

## URL Resolution & ZIP Extraction (`utils/download.py`)

SSK masters are distributed as ZIP archives containing a single CSV file.
The `resolve_csv()` context manager resolves a URL to a local CSV path transparently.

```python
@contextmanager
def resolve_csv(url: str, csv_glob: str = "*.csv") -> Generator[Path, None, None]:
    """Resolve URL → local CSV path.  Cleans up temp files on exit.

    Supported schemes:
      - https:// / http:// → download ZIP, extract matching CSV
      - file:// (ZIP)      → extract matching CSV to temp dir
      - file:// (CSV)      → yield path directly (no temp dir)

    Raises:
        DownloadError:    Network error, invalid ZIP, or no matching CSV
        FileNotFoundError: file:// target does not exist
        ValueError:        Unsupported scheme or file extension
    """
```

| URL scheme | Behaviour |
|---|---|
| `https://www.ssk.or.jp/.../s_ALL20260401.zip` | Download → extract → yield CSV |
| `file:///path/to/s_ALL20260401.zip` | Extract → yield CSV |
| `file:///path/to/s_ALL20260401.csv` | Yield directly (no extraction) |

**csv_glob per master type**:

| Script | csv_glob |
|---|---|
| `import_shinryo_koi.py` | `s_*.csv` |
| `import_iyakuhin.py` | `y_*.csv` |
| `import_shobyomei.py` | `b_*.csv` |

**SHA-256** is computed on the **extracted CSV file** (not the ZIP).
Temporary directories are cleaned up when the `with` block exits.

**Script-layer usage**:

```python
from mozc4med_dict.utils.download import resolve_csv, DownloadError

try:
    with resolve_csv(args.url, csv_glob="s_*.csv") as csv_path:
        importer = SskShinryoKoiImporter()
        count = importer.run(csv_path, args.url, args.imported_by)
except (DownloadError, FileNotFoundError, ValueError) as e:
    logger.error("%s", e)
    sys.exit(1)
```

> ⚠️ Download / extraction is handled at the **script layer**.
> `BaseImporter.run()` always receives a local `Path` — it does not know about URLs.

---

## `BaseImporter` Interface (`importers/base.py`)

All SSK importers must subclass `BaseImporter` and implement only `_parse()`.
SHA-256, batch creation, and UPSERT are owned by the base class — never re-implement them in a subclass.

```python
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
        """UPSERT via Postgres RPC (preserves dict_enabled)."""
        client.rpc(f"upsert_{self.source_type}",
                   {"records": records, "p_batch_id": batch_id}).execute()
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
                    change_type    = row[0],
                    is_active      = (row[23] == ""), # empty abolished_at → active
                )
                records.append(rec.model_dump())
        return records
```

### `change_type` Handling

`change_type` determines `is_active` in the parsed dict (set in `_parse()`).
`dict_enabled` is **never set in `_parse()`** — the RPC sets it `TRUE` for new records only.

| change_type | is_active |
|---|---|
| `1` (new) | `True` |
| `3` (modified) | `True` |
| `4` (abolished) | `False` |

---

## Custom CSV Import (`importers/csv_generic.py`)

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
| `pos_category` | — | `disease` / `drug` / `procedure` / `general` |
| `source_url` | — | Origin URL |
| `notes` | — | Free text |

---

## Python Exporter (`exporters/mozc_system_dict.py`)

```python
def export(output: Path) -> tuple[int, int]:
    """Export dictionary TSV. Returns (written, skipped)."""
    client = get_client()
    rows = client.rpc("export_mozc_dict", {"limit": 0}).execute().data  # ⚠️ default limit is 1000 rows; {"limit": 0} required for full export
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
    return written, skipped
```

---

## `utils/kana.py` — `normalize_reading()`

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
  ├─ 5. 長音符「ー」・中点「・」→ そのまま通す（カタカナ複合語向け）
  └─ 6. その他の残留文字（漢字・記号・全角英数等）→ ValueError
```

```python
def normalize_reading(raw: str) -> str:
    """Output: hiragana + ASCII digits + ー・ only. Raises ValueError otherwise."""
    raw = raw.strip().replace("\u3000", "")
    if not raw:
        raise ValueError("empty reading")
    s = jaconv.h2z(raw, kana=True, digit=False, ascii=False)
    s = alphabet2kana.alphabet2kana(s)
    s = jaconv.kata2hira(s)
    for ch in s:
        code = ord(ch)
        if 0x3041 <= code <= 0x3096:   # ひらがな
            continue
        if 0x30 <= code <= 0x39:        # 半角数字 0-9
            continue
        if ch in ("ー", "・"):
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
