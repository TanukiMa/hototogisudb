"""Integration test: Same file imported twice → second run aborts."""

from pathlib import Path

import pytest
from supabase import Client

from mozc4med_dict.importers.ssk_shobyomei import SskShobyomeiImporter


def _make_csv(tmp_path) -> Path:
    fields = [""] * 24
    fields[0] = "1"
    fields[2] = "1234567"
    fields[5] = "糖尿病"
    fields[9] = "トウニョウビョウ"
    path = tmp_path / "b_dedup.csv"
    path.write_bytes((",".join(fields) + "\r\n").encode("cp932"))
    return path


def test_duplicate_import_raises(client: Client, tmp_path):
    """同じファイル（同一SHA-256）を2回インポートするとValueErrorが発生する。"""
    csv_file = _make_csv(tmp_path)
    importer = SskShobyomeiImporter()

    importer.run(file_path=csv_file, imported_by="test")

    with pytest.raises(ValueError, match="already imported"):
        importer.run(file_path=csv_file, imported_by="test")


def test_duplicate_import_does_not_create_second_batch(client: Client, tmp_path):
    """2回目のインポートが失敗しても import_batches に2件目が作成されない。"""
    csv_file = _make_csv(tmp_path)
    importer = SskShobyomeiImporter()

    importer.run(file_path=csv_file, imported_by="test")

    try:
        importer.run(file_path=csv_file, imported_by="test")
    except ValueError:
        pass

    batches = (
        client.table("import_batches")
        .select("id")
        .eq("source_type", "ssk_shobyomei")
        .execute()
        .data
    )
    assert len(batches) == 1, "import_batches must have exactly one entry after duplicate attempt"
