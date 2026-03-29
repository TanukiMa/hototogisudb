import csv
import logging
from pathlib import Path

from mozc4med_dict.db import get_client
from mozc4med_dict.importers.base import BaseImporter

logger = logging.getLogger(__name__)

_F_CHANGE_TYPE = 0
_F_CODE = 2
_F_ABBR_KANJI = 4
_F_ABBR_KANA = 6
_F_CHANGED_AT = 86
_F_ABOLISHED_AT = 87
_F_BASE_KANJI = 112


def _parse_date(s: str) -> str | None:
    s = s.strip()
    if not s or s == "0":
        return None
    if len(s) == 8:
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return None


class SskShinryoKoiImporter(BaseImporter):
    source_type = "ssk_shinryo_koi"

    def _parse_rows(self, file_path: Path, batch_id: int) -> list[dict]:
        rows = []
        with file_path.open(encoding="cp932", errors="replace", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 113:
                    continue
                change_type = row[_F_CHANGE_TYPE].strip()
                is_active = change_type != "4"
                record: dict = {
                    "shinryo_koi_code": row[_F_CODE].strip(),
                    "abbr_kanji_name": row[_F_ABBR_KANJI].strip() or None,
                    "abbr_kana_name": row[_F_ABBR_KANA].strip() or None,
                    "base_kanji_name": row[_F_BASE_KANJI].strip() or None,
                    "change_type": change_type or None,
                    "changed_at": _parse_date(row[_F_CHANGED_AT]),
                    "abolished_at": _parse_date(row[_F_ABOLISHED_AT]),
                    "is_active": is_active,
                    "batch_id": batch_id,
                }
                rows.append(record)
        return rows

    def _upsert_rows(self, rows: list[dict]) -> int:
        if not rows:
            return 0
        client = get_client()
        client.table("ssk_shinryo_koi").upsert(
            rows,
            on_conflict="shinryo_koi_code",
        ).execute()
        return len(rows)
