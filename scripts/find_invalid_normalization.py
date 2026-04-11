"""Find entries that would fail normalize_reading during export.
Writes a JSON file `invalid_entries.json` with the raw rows.
"""
import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

from mozc4med_dict.db import get_client
from mozc4med_dict.utils.kana import normalize_reading


def main() -> None:
    client = get_client()
    # Retrieve all export rows
    result = client.rpc("export_mozc_dict", {}).execute()
    rows = result.data or []
    invalid = []
    for row in rows:
        raw = row.get("raw_reading")
        try:
            # normalize_reading expects a string; if None, it will raise
            normalize_reading(str(raw) if raw is not None else "")
        except Exception as e:
            # Keep the original row and error message
            row_copy = dict(row)
            row_copy["error"] = str(e)
            invalid.append(row_copy)
    out_path = Path("invalid_entries.json")
    out_path.write_text(json.dumps(invalid, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Found {len(invalid)} invalid entries, written to {out_path}")

if __name__ == "__main__":
    main()
