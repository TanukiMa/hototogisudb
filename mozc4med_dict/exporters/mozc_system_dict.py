import logging
from pathlib import Path
from typing import Any

from mozc4med_dict.db import get_client
from mozc4med_dict.models import MozcDictEntry
from mozc4med_dict.utils.kana import normalize_reading

logger = logging.getLogger(__name__)

_RPC_FUNCTION = "export_mozc_dict"


class MozcSystemDictExporter:
    """全テーブルの dict_enabled=TRUE エントリを Mozc 辞書 TSV に出力する。"""

    @staticmethod
    def _rows_from_rpc(data: object) -> list[dict[str, Any]]:
        if data is None:
            return []
        if not isinstance(data, list):
            raise ValueError(f"Export RPC returned unexpected payload type: {type(data).__name__}")
        rows: list[dict[str, Any]] = []
        for index, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(f"Export RPC row[{index}] is not an object")
            rows.append(item)
        return rows

    @staticmethod
    def _build_entry(row: dict[str, Any]) -> MozcDictEntry:
        reading_raw = row.get("raw_reading")
        if not isinstance(reading_raw, str):
            raise ValueError(f"Invalid raw_reading value: {reading_raw!r}")
        reading = normalize_reading(reading_raw)

        left_id = row.get("left_id")
        right_id = row.get("right_id")
        cost = row.get("cost")
        surface_form = row.get("surface_form")
        if not isinstance(left_id, int):
            raise ValueError(f"Invalid left_id value: {left_id!r}")
        if not isinstance(right_id, int):
            raise ValueError(f"Invalid right_id value: {right_id!r}")
        if not isinstance(cost, int):
            raise ValueError(f"Invalid cost value: {cost!r}")
        if not isinstance(surface_form, str):
            raise ValueError(f"Invalid surface_form value: {surface_form!r}")

        return MozcDictEntry(
            reading=reading,
            left_id=left_id,
            right_id=right_id,
            cost=cost,
            surface_form=surface_form,
        )

    def export(
        self,
        output_path: Path,
        dry_run: bool = False,
        no_skip: bool = False,
        include_invalid: bool = False,
    ) -> tuple[int, int]:
        """Export dictionary TSV. Returns (written, skipped)."""
        client = get_client()

        rows = []
        offset = 0
        while True:
            # PostgREST の max_rows 制限を回避するため、オフセットを用いてページネーションを行う
            result = client.rpc(_RPC_FUNCTION, {"p_offset": offset}).execute()
            batch = self._rows_from_rpc(result.data)

            if not batch:
                break

            rows.extend(batch)
            if len(batch) < 1000:
                break
            offset += len(batch)

        logger.info("Fetched %d entries from DB", len(rows))

        if dry_run:
            logger.info("Dry-run mode: skipping file write")
            return len(rows), 0

        written = skipped = 0
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8", newline="\n") as f:
            for r in rows:
                try:
                    entry = self._build_entry(r)
                except ValueError as e:
                    if no_skip or include_invalid:
                        # normalize_reading が失敗した、または raw_reading が NULL の場合はそのまま書き込む
                        # `raw_reading` が None のときは空文字列にフォールバック
                        reading_raw = r.get("raw_reading") or ""
                        left_id = r.get("left_id")
                        right_id = r.get("right_id")
                        cost = r.get("cost")
                        surface_form = r.get("surface_form")
                        entry = MozcDictEntry(
                            reading=str(reading_raw),
                            left_id=int(left_id) if isinstance(left_id, (int, float)) else 1849,
                            right_id=int(right_id) if isinstance(right_id, (int, float)) else 1849,
                            cost=int(cost) if isinstance(cost, (int, float)) else 5000,
                            surface_form=str(surface_form),
                        )
                        logger.info(
                            "fallback (%s): %s -> %s",
                            "include-invalid" if include_invalid else "no-skip",
                            reading_raw,
                            entry.reading,
                        )
                    else:
                        surface = r.get("surface_form")
                        logger.warning("skipped: %s (surface=%s)", e, surface)
                        skipped += 1
                        continue
                    f.write(entry.to_tsv_line() + "\n")
                    written += 1

        logger.info("Written %d entries to %s (%d skipped)", written, output_path, skipped)
        return written, skipped
