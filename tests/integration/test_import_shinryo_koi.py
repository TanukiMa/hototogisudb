"""Integration test: SskShinryoKoiImporter — CSV → DB round-trip."""

from pathlib import Path

import pytest
from supabase import Client

from mozc4med_dict.importers.ssk_shinryo_koi import SskShinryoKoiImporter


def _make_row(
    code: str = "123456789",
    abbr_kanji: str = "初診料",
    abbr_kana: str = "ショシンリョウ",
    change_type: str = "1",
    abolished_at: str = "",
) -> list[str]:
    fields = [""] * 113
    fields[0] = change_type
    fields[2] = code
    fields[4] = abbr_kanji
    fields[6] = abbr_kana
    fields[87] = abolished_at
    fields[112] = f"{abbr_kanji}（基本）"
    return fields


def _make_csv(tmp_path, rows: list[list[str]]) -> Path:
    path = tmp_path / "s_test.csv"
    lines = [",".join(r).encode("cp932") + b"\r\n" for r in rows]
    path.write_bytes(b"".join(lines))
    return path


def test_import_shinryo_koi_inserts_record(client: Client, tmp_path):
    csv_file = _make_csv(tmp_path, [_make_row()])
    importer = SskShinryoKoiImporter()
    count = importer.run(file_path=csv_file, imported_by="test")

    assert count == 1
    rows = client.table("ssk_shinryo_koi").select("*").eq("shinryo_koi_code", "123456789").execute().data
    assert len(rows) == 1
    assert rows[0]["abbr_kanji_name"] == "初診料"
    assert rows[0]["abbr_kana_name"] == "しょしんりょう"
    assert rows[0]["is_active"] is True
    assert rows[0]["dict_enabled"] is True


def test_import_shinryo_koi_abolished_sets_inactive(client: Client, tmp_path):
    csv_file = _make_csv(
        tmp_path,
        [_make_row(change_type="4", abolished_at="20240401")],
    )
    importer = SskShinryoKoiImporter()
    importer.run(file_path=csv_file, imported_by="test")

    row = (
        client.table("ssk_shinryo_koi")
        .select("is_active")
        .eq("shinryo_koi_code", "123456789")
        .single()
        .execute()
        .data
    )
    assert row["is_active"] is False
