"""Integration test: SskIyakuhinImporter — CSV → DB round-trip."""

from pathlib import Path

import pytest
from supabase import Client

from mozc4med_dict.importers.ssk_iyakuhin import SskIyakuhinImporter


def _make_row(
    code: str = "100000001",
    kanji: str = "アスピリン錠",
    kana: str = "アスピリンジョウ",
    is_generic: str = "0",
    change_type: str = "1",
    generic_label: str = "アスピリン錠100mg",
) -> list[str]:
    fields = [""] * 38
    fields[0] = change_type
    fields[2] = code
    fields[4] = kanji
    fields[6] = kana
    fields[16] = is_generic
    fields[37] = generic_label
    return fields


def _make_csv(tmp_path, rows: list[list[str]]) -> Path:
    path = tmp_path / "y_test.csv"
    lines = [",".join(r).encode("cp932") + b"\r\n" for r in rows]
    path.write_bytes(b"".join(lines))
    return path


def test_import_iyakuhin_inserts_record(client: Client, tmp_path):
    csv_file = _make_csv(tmp_path, [_make_row()])
    importer = SskIyakuhinImporter()
    count = importer.run(file_path=csv_file, imported_by="test")

    assert count == 1
    rows = client.table("ssk_iyakuhin").select("*").eq("iyakuhin_code", "100000001").execute().data
    assert len(rows) == 1
    assert rows[0]["kanji_name"] == "アスピリン錠"
    assert rows[0]["kana_name"] == "あすぴりんじょう"
    assert rows[0]["is_active"] is True
    assert rows[0]["dict_enabled"] is True


def test_import_iyakuhin_generic_flag(client: Client, tmp_path):
    csv_file = _make_csv(tmp_path, [_make_row(is_generic="1")])
    importer = SskIyakuhinImporter()
    importer.run(file_path=csv_file, imported_by="test")

    row = client.table("ssk_iyakuhin").select("is_generic").eq("iyakuhin_code", "100000001").single().execute().data
    assert row["is_generic"] is True
