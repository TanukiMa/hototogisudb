import hashlib
import logging
from abc import ABC, abstractmethod
from pathlib import Path

from mozc4med_dict.db import get_client
from supabase import Client

logger = logging.getLogger(__name__)


class BaseImporter(ABC):
    """Base class for all SSK master importers with SHA-256 duplicate detection."""

    source_type: str  # サブクラスで定義

    @abstractmethod
    def _parse(self, file_path: Path) -> list[dict[str, object]]:
        """CSV を読み込んで upsert 用の dict リストを返す。"""

    def _rows_from_response(
        self, data: object, *, context: str, allow_none: bool = False
    ) -> list[dict[str, object]]:
        if data is None:
            if allow_none:
                return []
            raise ValueError(f"{context} returned no data")
        if not isinstance(data, list):
            raise ValueError(f"{context} returned unexpected payload type: {type(data).__name__}")

        rows: list[dict[str, object]] = []
        for index, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(f"{context} row[{index}] is not an object")
            rows.append(item)
        return rows

    def _abort_if_duplicate(self, client: Client, file_name: str, sha256: str) -> None:
        """Raise ValueError if this file was already imported (SHA-256 match)."""
        existing = (
            client.table("import_batches")
            .select("id")
            .eq("file_sha256", sha256)
            .execute()
        )
        existing_rows = self._rows_from_response(
            existing.data, context="import_batches duplicate check", allow_none=True
        )
        if existing_rows:
            existing_id = existing_rows[0].get("id")
            raise ValueError(
                f"File {file_name} (sha256={sha256}) was already imported "
                f"(batch_id={existing_id})"
            )

    def _sha256(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file for duplicate detection."""
        sha = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def _compute_sha256(self, file_path: Path) -> str:
        """Backward-compatible alias of _sha256()."""
        return self._sha256(file_path)

    def run(
        self,
        file_path: Path,
        source_url: str | None = None,
        imported_by: str | None = None,
        notes: str | None = None,
    ) -> int:
        """
        Main import flow:
        1. Compute SHA-256 of input file
        2. Check import_batches for duplicate (prevent re-import)
        3. INSERT new batch row, capture batch_id
        4. UPSERT records
        5. UPDATE record_count on batch

        Returns number of records imported.
        """
        client = get_client()
        sha256 = self._sha256(file_path)
        self._abort_if_duplicate(client, file_path.name, sha256)

        # バッチ登録
        batch_row: dict[str, str | None] = {
            "source_type": self.source_type,
            "source_url": source_url,
            "file_name": file_path.name,
            "file_sha256": sha256,
            "imported_by": imported_by,
            "notes": notes,
        }
        result = client.table("import_batches").insert(batch_row).execute()
        inserted_rows = self._rows_from_response(result.data, context="import_batches insert")
        if not inserted_rows:
            raise ValueError("import_batches insert returned no rows")
        raw_batch_id = inserted_rows[0].get("id")
        if not isinstance(raw_batch_id, int):
            raise ValueError(f"import_batches insert returned invalid id: {raw_batch_id!r}")
        batch_id = raw_batch_id
        logger.info("Created import batch id=%d for %s", batch_id, file_path.name)

        # レコード処理
        records = self._parse(file_path)
        client.rpc(
            f"upsert_{self.source_type}", {"records": records, "p_batch_id": batch_id}
        ).execute()
        count = len(records)

        # record_count 更新
        client.table("import_batches").update({"record_count": count}).eq("id", batch_id).execute()
        logger.info("Imported %d records (batch_id=%d)", count, batch_id)
        return count
