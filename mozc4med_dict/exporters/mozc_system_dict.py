import logging
from pathlib import Path

from mozc4med_dict.db import get_client
from mozc4med_dict.models import MozcDictEntry
from mozc4med_dict.utils.kana import normalize_reading

logger = logging.getLogger(__name__)

_RPC_FUNCTION = "export_mozc_dict_entries"


class MozcSystemDictExporter:
    """全テーブルの dict_enabled=TRUE エントリを Mozc 辞書 TSV に出力する。"""

    def export(
        self,
        output_path: Path,
        dry_run: bool = False,
    ) -> tuple[int, int]:
        """Export dictionary TSV. Returns (written, skipped)."""
        client = get_client()
        # Supabase RPC のデフォルトは 1000 行まで。全件取得するため limit=0 を指定
        result = client.rpc(_RPC_FUNCTION, {"limit": 0}).execute()
        rows = result.data

        logger.info("Fetched %d entries from DB", len(rows))

        if dry_run:
            logger.info("Dry-run mode: skipping file write")
            return len(rows), 0

        written = skipped = 0
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8", newline="\n") as f:
            for r in rows:
                try:
                    reading = normalize_reading(r["reading"])
                except ValueError as e:
                    logger.warning("skipped: %s (surface=%s)", e, r["surface_form"])
                    skipped += 1
                    continue
                entry = MozcDictEntry(
                    reading=reading,
                    left_id=r["left_id"],
                    right_id=r["right_id"],
                    cost=r["cost"],
                    surface_form=r["surface_form"],
                )
                f.write(entry.to_tsv_line() + "\n")
                written += 1

        logger.info("Written %d entries to %s (%d skipped)", written, output_path, skipped)
        return written, skipped
