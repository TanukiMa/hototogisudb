import csv
import logging
from pathlib import Path

from mozc4med_dict.db import get_client
from mozc4med_dict.importers.base import BaseImporter
from mozc4med_dict.utils.kana import normalize_reading

logger = logging.getLogger(__name__)


def _safe_normalize(kana: str) -> str | None:
    if not kana:
        return None
    try:
        return normalize_reading(kana)
    except ValueError as e:
        logger.debug("カナ正規化スキップ %r: %s", kana, e)
        return None


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

    def _parse_rows(self, file_path: Path, batch_id: int) -> list[dict]:
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
                    "batch_id": batch_id,
                }
                rows.append(record)
        return rows

    def _upsert_rows(self, rows: list[dict]) -> int:
        if not rows:
            return 0
        client = get_client()
        client.table("ssk_iyakuhin").upsert(
            rows,
            on_conflict="iyakuhin_code",
        ).execute()
        return len(rows)
