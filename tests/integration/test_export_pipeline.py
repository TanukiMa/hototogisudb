"""Integration test: DB → TSV export pipeline."""


from mozc4med_dict.exporters.mozc_system_dict import MozcSystemDictExporter
from supabase import Client


def _insert_shobyomei(client: Client, code: str, base_name: str, kana: str) -> None:
    """直接DBにレコードを挿入してエクスポートのテストデータを準備する。"""
    client.table("ssk_shobyomei").insert(
        {
            "shobyomei_code": code,
            "base_name": base_name,
            "kana_name": kana,
            "is_active": True,
            "dict_enabled": True,
        }
    ).execute()


def _insert_custom_term(client: Client, surface: str, reading: str, cost: int) -> None:
    client.table("custom_terms").insert(
        {
            "surface_form": surface,
            "reading": reading,
            "cost": cost,
            "dict_enabled": True,
        }
    ).execute()


def test_export_produces_tsv_lines(client: Client, tmp_path):
    """dict_enabled=TrueのレコードがTSVに出力される。"""
    _insert_shobyomei(client, "1234567", "糖尿病", "とうにょうびょう")

    output = tmp_path / "out.txt"
    exporter = MozcSystemDictExporter()
    count = exporter.export(output_path=output)

    assert count >= 1
    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == count
    # TSV形式: reading\tleft_id\tright_id\tcost\tsurface_form
    fields = lines[0].split("\t")
    assert len(fields) == 5


def test_export_excludes_dict_disabled(client: Client, tmp_path):
    """dict_enabled=Falseのレコードはエクスポートされない。"""
    _insert_shobyomei(client, "1234567", "糖尿病", "とうにょうびょう")
    client.table("ssk_shobyomei").update({"dict_enabled": False}).eq(
        "shobyomei_code", "1234567"
    ).execute()

    output = tmp_path / "out.txt"
    exporter = MozcSystemDictExporter()
    count = exporter.export(output_path=output)

    assert count == 0
    assert output.read_text(encoding="utf-8") == ""


def test_export_dry_run_does_not_write_file(client: Client, tmp_path):
    """dry_run=Trueではファイルが作成されない。"""
    _insert_shobyomei(client, "1234567", "糖尿病", "とうにょうびょう")

    output = tmp_path / "dry_out.txt"
    exporter = MozcSystemDictExporter()
    count = exporter.export(output_path=output, dry_run=True)

    assert count >= 1
    assert not output.exists(), "dry_runではファイルを書き出してはならない"


def test_export_lf_line_endings(client: Client, tmp_path):
    """出力ファイルの改行コードがLF(\\n)であること。"""
    _insert_shobyomei(client, "1234567", "糖尿病", "とうにょうびょう")

    output = tmp_path / "out.txt"
    exporter = MozcSystemDictExporter()
    exporter.export(output_path=output)

    raw = output.read_bytes()
    assert b"\r\n" not in raw, "出力ファイルにCRLFが含まれてはならない"
