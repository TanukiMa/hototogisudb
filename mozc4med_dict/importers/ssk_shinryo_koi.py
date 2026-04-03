import csv
from pathlib import Path
from typing import Any

from mozc4med_dict.importers.base import BaseImporter

# 正規化はエクスポート時にのみ行うため、インポート時は生データを保持

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
        year, month, day = s[:4], s[4:6], s[6:8]
        if month == "99" or day == "99":
            return None
        return f"{year}-{month}-{day}"
    return None


class SskShinryoKoiImporter(BaseImporter):
    source_type = "ssk_shinryo_koi"

    def _parse(self, file_path: Path) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        with file_path.open(encoding="cp932", errors="replace", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 113:
                    continue
                change_type = row[_F_CHANGE_TYPE].strip()
                is_active = change_type != "4"
                record: dict[str, Any] = {
                    "shinryo_koi_code": row[_F_CODE].strip(),
                    "abbr_kanji_name": row[_F_ABBR_KANJI].strip() or None,
                    "abbr_kana_name": row[_F_ABBR_KANA].strip() or None,
                    "base_kanji_name": row[_F_BASE_KANJI].strip() or None,
                    "change_type": change_type or None,
                    "changed_at": _parse_date(row[_F_CHANGED_AT]),
                    "abolished_at": _parse_date(row[_F_ABOLISHED_AT]),
                    "is_active": is_active,
                }
                rows.append(record)
        return rows
