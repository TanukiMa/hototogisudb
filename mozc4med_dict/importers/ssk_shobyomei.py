import csv
import logging
from pathlib import Path

from mozc4med_dict.db import get_client
from mozc4med_dict.importers.base import BaseImporter

logger = logging.getLogger(__name__)

_F_CHANGE_TYPE = 0
_F_CODE = 2
_F_SUCCESSOR = 3
_F_BASE_NAME = 5
_F_ABBR_NAME = 7
_F_KANA_NAME = 9
_F_MGMT_CODE = 10
_F_ADOPTION = 11
_F_ICD10_1 = 15
_F_ICD10_2 = 16
_F_LISTED_AT = 21
_F_CHANGED_AT = 22
_F_ABOLISHED_AT = 23


def _parse_date(s: str) -> str | None:
    s = s.strip()
    if not s or s == "0":
        return None
    if len(s) == 8:
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return None


class SskShobyomeiImporter(BaseImporter):
    source_type = "ssk_shobyomei"

    def _parse_rows(self, file_path: Path, batch_id: int) -> list[dict]:
        rows = []
        with file_path.open(encoding="cp932", errors="replace", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 24:
                    continue
                change_type = row[_F_CHANGE_TYPE].strip()
                is_active = change_type != "4"
                record: dict = {
                    "shobyomei_code": row[_F_CODE].strip(),
                    "successor_code": row[_F_SUCCESSOR].strip() or None,
                    "base_name": row[_F_BASE_NAME].strip() or None,
                    "abbr_name": row[_F_ABBR_NAME].strip() or None,
                    "kana_name": row[_F_KANA_NAME].strip() or None,
                    "byomei_mgmt_code": row[_F_MGMT_CODE].strip() or None,
                    "adoption_type": row[_F_ADOPTION].strip() or None,
                    "icd10_1": row[_F_ICD10_1].strip() or None,
                    "icd10_2": row[_F_ICD10_2].strip() or None,
                    "change_type": change_type or None,
                    "listed_at": _parse_date(row[_F_LISTED_AT]),
                    "changed_at": _parse_date(row[_F_CHANGED_AT]),
                    "abolished_at": _parse_date(row[_F_ABOLISHED_AT]),
                    "is_active": is_active,
                    "batch_id": batch_id,
                }
                if change_type == "1":
                    record["dict_enabled"] = True
                rows.append(record)
        return rows

    def _upsert_rows(self, rows: list[dict]) -> int:
        if not rows:
            return 0
        client = get_client()
        client.table("ssk_shobyomei").upsert(
            rows,
            on_conflict="shobyomei_code",
        ).execute()
        return len(rows)
