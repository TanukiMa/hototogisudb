import csv
import logging
from pathlib import Path

from mozc4med_dict.db import get_client
from mozc4med_dict.utils.kana import normalize_reading

logger = logging.getLogger(__name__)


class CsvGenericImporter:
    """カスタム CSV を custom_terms テーブルにインポートする。

    CSV フォーマット (UTF-8, ヘッダーあり):
        surface_form,reading,cost,pos_type_id,source_label,source_url,notes
    """

    def import_file(
        self,
        file_path: Path,
        source_label: str | None = None,
    ) -> int:
        rows = []
        with file_path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cost_raw = row.get("cost", "").strip()
                reading = normalize_reading(row.get("reading", "").strip())
                record: dict = {
                    "surface_form": row["surface_form"].strip(),
                    "reading": reading,
                    "cost": int(cost_raw) if cost_raw else 5000,
                    "source_label": row.get("source_label", "").strip() or source_label or None,
                    "source_url": row.get("source_url", "").strip() or None,
                    "notes": row.get("notes", "").strip() or None,
                }
                pos_raw = row.get("pos_type_id", "").strip()
                if pos_raw:
                    record["pos_type_id"] = int(pos_raw)
                rows.append(record)

        if not rows:
            return 0

        client = get_client()
        client.table("custom_terms").upsert(
            rows,
            on_conflict="surface_form,reading",
        ).execute()
        logger.info("Imported %d custom terms", len(rows))
        return len(rows)
