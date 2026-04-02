"""CRITICAL: dict_enabled must not be overwritten on re-import for any SSK importer."""

from pathlib import Path

from mozc4med_dict.importers.ssk_iyakuhin import SskIyakuhinImporter
from mozc4med_dict.importers.ssk_shinryo_koi import SskShinryoKoiImporter
from mozc4med_dict.importers.ssk_shobyomei import SskShobyomeiImporter
from supabase import Client

# --- helpers ---

def _shobyomei_csv(tmp_path, name: str) -> Path:
    fields = [""] * 24
    fields[0] = "1"
    fields[2] = "1234567"
    fields[5] = "糖尿病"
    fields[9] = "トウニョウビョウ"
    path = tmp_path / name
    path.write_bytes((",".join(fields) + "\r\n").encode("cp932"))
    return path


def _iyakuhin_csv(tmp_path, name: str) -> Path:
    fields = [""] * 38
    fields[0] = "1"
    fields[2] = "100000001"
    fields[4] = "アスピリン錠"
    fields[6] = "アスピリンジョウ"
    path = tmp_path / name
    path.write_bytes((",".join(fields) + "\r\n").encode("cp932"))
    return path


def _shinryo_csv(tmp_path, name: str) -> Path:
    fields = [""] * 113
    fields[0] = "1"
    fields[2] = "123456789"
    fields[4] = "初診料"
    fields[6] = "ショシンリョウ"
    path = tmp_path / name
    path.write_bytes((",".join(fields) + "\r\n").encode("cp932"))
    return path


# --- tests ---

def test_shobyomei_upsert_does_not_overwrite_dict_enabled(client: Client, tmp_path):
    """管理者がdict_enabled=Falseに設定した後、再インポートしてもFalseのまま。"""
    importer = SskShobyomeiImporter()
    importer.run(file_path=_shobyomei_csv(tmp_path, "b_first.csv"), imported_by="test")

    client.table("ssk_shobyomei").update({"dict_enabled": False}).eq(
        "shobyomei_code", "1234567"
    ).execute()

    # 別ファイル名（別SHA）で同じレコードを再インポート
    csv2 = _shobyomei_csv(tmp_path, "b_second.csv")
    csv2.write_bytes(csv2.read_bytes() + b" ")  # SHA変更のため末尾に空白追加
    importer.run(file_path=csv2, imported_by="test")

    row = (
        client.table("ssk_shobyomei")
        .select("dict_enabled")
        .eq("shobyomei_code", "1234567")
        .single()
        .execute()
        .data
    )
    assert row["dict_enabled"] is False, "re-import must not overwrite dict_enabled=False"


def test_iyakuhin_upsert_does_not_overwrite_dict_enabled(client: Client, tmp_path):
    importer = SskIyakuhinImporter()
    importer.run(file_path=_iyakuhin_csv(tmp_path, "y_first.csv"), imported_by="test")

    client.table("ssk_iyakuhin").update({"dict_enabled": False}).eq(
        "iyakuhin_code", "100000001"
    ).execute()

    csv2 = _iyakuhin_csv(tmp_path, "y_second.csv")
    csv2.write_bytes(csv2.read_bytes() + b" ")
    importer.run(file_path=csv2, imported_by="test")

    row = (
        client.table("ssk_iyakuhin")
        .select("dict_enabled")
        .eq("iyakuhin_code", "100000001")
        .single()
        .execute()
        .data
    )
    assert row["dict_enabled"] is False, "re-import must not overwrite dict_enabled=False"


def test_shinryo_koi_upsert_does_not_overwrite_dict_enabled(client: Client, tmp_path):
    importer = SskShinryoKoiImporter()
    importer.run(file_path=_shinryo_csv(tmp_path, "s_first.csv"), imported_by="test")

    client.table("ssk_shinryo_koi").update({"dict_enabled": False}).eq(
        "shinryo_koi_code", "123456789"
    ).execute()

    csv2 = _shinryo_csv(tmp_path, "s_second.csv")
    csv2.write_bytes(csv2.read_bytes() + b" ")
    importer.run(file_path=csv2, imported_by="test")

    row = (
        client.table("ssk_shinryo_koi")
        .select("dict_enabled")
        .eq("shinryo_koi_code", "123456789")
        .single()
        .execute()
        .data
    )
    assert row["dict_enabled"] is False, "re-import must not overwrite dict_enabled=False"
