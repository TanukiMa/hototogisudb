import csv
import logging
from pathlib import Path

from mozc4med_dict.db import get_client
from mozc4med_dict.importers.base import BaseImporter
# 正規化はエクスポート時にのみ行うため、インポート時は生データを保持

def _safe_normalize(kana: str) -> str | None:
    return kana or None


_F_CHANGE_TYPE = 0
_F_CODE = 2
_F_KANJI_NAME = 4
_F_KANA_NAME = 6
_F_IS_GENERIC = 16
_F_CHANGED_AT = 29
_F_ABOLISHED_AT = 30
_F_BASE_KANJI = 34
_F_GENERIC_CODE = 36
_F_GENERIC_LABEL = 37


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


class SskIyakuhinImporter(BaseImporter):
    source_type = "ssk_iyakuhin"

    def _parse(self, file_path: Path) -> list[dict]:
        rows = []
        with file_path.open(encoding="cp932", errors="replace", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 38:
                    continue
                change_type = row[_F_CHANGE_TYPE].strip()
                is_active = change_type != "4"
                is_generic = row[_F_IS_GENERIC].strip() == "1"
                record: dict = {
                    "iyakuhin_code": row[_F_CODE].strip(),
                    "kanji_name": row[_F_KANJI_NAME].strip() or None,
                    "kana_name": _safe_normalize(row[_F_KANA_NAME].strip()),
                    "base_kanji_name": row[_F_BASE_KANJI].strip() or None,
                    "generic_name_code": row[_F_GENERIC_CODE].strip() or None,
                    "generic_name_label": row[_F_GENERIC_LABEL].strip() or None,
                    "is_generic": is_generic,
                    "change_type": change_type or None,
                    "changed_at": _parse_date(row[_F_CHANGED_AT]),
                    "abolished_at": _parse_date(row[_F_ABOLISHED_AT]),
                    "is_active": is_active,
                }
                rows.append(record)
        return rows

