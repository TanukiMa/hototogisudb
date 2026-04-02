import logging
from pathlib import Path

from mozc4med_dict.db import get_client
from mozc4med_dict.models import MozcDictEntry

logger = logging.getLogger(__name__)

_RPC_FUNCTION = "export_mozc_dict_entries"


class MozcSystemDictExporter:
    """全テーブルの dict_enabled=TRUE エントリを Mozc 辞書 TSV に出力する。"""

    def export(
        self,
        output_path: Path,
        dry_run: bool = False,
    ) -> int:
        client = get_client()
        # Supabase RPC のデフォルトは 1000 行まで。全件取得するため limit=0 を指定
        result = client.rpc(_RPC_FUNCTION, {"limit": 0}).execute()
        rows = result.data

        entries = [
            MozcDictEntry(
                reading=r["reading"],
                left_id=r["left_id"],
                right_id=r["right_id"],
                cost=r["cost"],
                surface_form=r["surface_form"],
            )
            for r in rows
        ]

        count = len(entries)
        logger.info("Fetched %d entries from DB", count)

        if dry_run:
            logger.info("Dry-run mode: skipping file write")
            return count

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8", newline="\n") as f:
            for entry in entries:
                f.write(entry.to_tsv_line() + "\n")

        logger.info("Written to %s", output_path)
        return count
