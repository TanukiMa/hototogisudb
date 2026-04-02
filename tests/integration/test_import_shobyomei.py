"""Integration test: SskShobyomeiImporter — CSV → DB round-trip."""

from pathlib import Path

from mozc4med_dict.importers.ssk_shobyomei import SskShobyomeiImporter
from supabase import Client


def _make_csv(tmp_path, rows: list[list[str]]) -> Path:
    path = tmp_path / "b_test.csv"
    lines = []
    for fields in rows:
        lines.append(",".join(fields).encode("cp932") + b"\r\n")
    path.write_bytes(b"".join(lines))
    return path


def _make_row(
    code: str = "1234567",
    base_name: str = "糖尿病",
    kana: str = "トウニョウビョウ",
    change_type: str = "1",
    abolished_at: str = "",
) -> list[str]:
    fields = [""] * 24
    fields[0] = change_type
    fields[2] = code
    fields[5] = base_name
    fields[9] = kana
    fields[23] = abolished_at
    return fields


def test_import_shobyomei_inserts_record(client: Client, tmp_path):
    csv_file = _make_csv(tmp_path, [_make_row()])
    importer = SskShobyomeiImporter()
    count = importer.run(file_path=csv_file, source_url="http://example.com", imported_by="test")

    assert count == 1
    rows = client.table("ssk_shobyomei").select("*").eq("shobyomei_code", "1234567").execute().data
    assert len(rows) == 1
    assert rows[0]["base_name"] == "糖尿病"
    # インポート時は生データを保持（正規化はエクスポート時に行う）
    assert rows[0]["kana_name"] == "トウニョウビョウ"
    assert rows[0]["is_active"] is True
    assert rows[0]["dict_enabled"] is True


def test_import_shobyomei_abolished_sets_inactive(client: Client, tmp_path):
    csv_file = _make_csv(
        tmp_path,
        [_make_row(change_type="4", abolished_at="20240101")],
    )
    importer = SskShobyomeiImporter()
    importer.run(file_path=csv_file, imported_by="test")

    row = (
        client.table("ssk_shobyomei")
        .select("is_active")
        .eq("shobyomei_code", "1234567")
        .single()
        .execute()
        .data
    )
    assert row["is_active"] is False
