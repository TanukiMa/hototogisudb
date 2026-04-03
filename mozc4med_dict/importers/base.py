import hashlib
import logging
from abc import ABC, abstractmethod
from pathlib import Path

from supabase import Client

from mozc4med_dict.db import get_client

logger = logging.getLogger(__name__)


class BaseImporter(ABC):
    """Base class for all SSK master importers with SHA-256 duplicate detection."""

    source_type: str  # サブクラスで定義

    @abstractmethod
    def _parse(self, file_path: Path) -> list[dict]:
        """CSV を読み込んで upsert 用の dict リストを返す。"""

    def _abort_if_duplicate(self, client: Client, file_name: str, sha256: str) -> None:
        """Raise ValueError if this file was already imported (SHA-256 match)."""
        existing = (
            client.table("import_batches")
            .select("id")
            .eq("file_sha256", sha256)
            .execute()
        )
        if existing.data:
            raise ValueError(
                f"File {file_name} (sha256={sha256}) was already imported "
                f"(batch_id={existing.data[0]['id']})"
            )

    def _compute_sha256(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file for duplicate detection."""
        sha = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()

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
        sha256 = self._compute_sha256(file_path)
        self._abort_if_duplicate(client, file_path.name, sha256)

        # バッチ登録
        batch_row = {
            "source_type": self.source_type,
            "source_url": source_url,
            "file_name": file_path.name,
            "file_sha256": sha256,
            "imported_by": imported_by,
            "notes": notes,
        }
        result = client.table("import_batches").insert(batch_row).execute()
        batch_id: int = result.data[0]["id"]
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
