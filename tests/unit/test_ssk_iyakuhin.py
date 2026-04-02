from unittest.mock import MagicMock, patch

from mozc4med_dict.importers.ssk_iyakuhin import SskIyakuhinImporter


def test_ssk_iyakuhin_parse_row(tmp_path):
    fields = [""] * 38
    fields[0] = "1"
    fields[2] = "100000001"
    fields[4] = "アスピリン錠"
    fields[6] = "アスピリンジョウ"
    fields[16] = "0"
    fields[29] = ""
    fields[30] = ""
    fields[34] = "アスピリン錠（基本）"
    fields[36] = "GEN001"
    fields[37] = "アスピリン錠100mg"

    line = ",".join(fields).encode("cp932")
    csv_file = tmp_path / "y_test.csv"
    csv_file.write_bytes(line + b"\r\n")

    mock_client = MagicMock()
    t = mock_client.table.return_value
    t.select.return_value.eq.return_value.execute.return_value.data = []
    t.insert.return_value.execute.return_value.data = [{"id": 55}]
    t.update.return_value.eq.return_value.execute.return_value.data = []
    mock_client.rpc.return_value.execute.return_value.data = [{}]

    with patch("mozc4med_dict.importers.base.get_client", return_value=mock_client):
        importer = SskIyakuhinImporter()
        count = importer.run(file_path=csv_file, imported_by="test")

    assert count == 1
    rpc_call = mock_client.rpc.call_args
    assert rpc_call[0][0] == "upsert_ssk_iyakuhin"
    record = rpc_call[0][1]["records"][0]
    assert record["iyakuhin_code"] == "100000001"
    assert record["kanji_name"] == "アスピリン錠"
    # 正規化せず、生データが保存される
    assert record["kana_name"] == "アスピリンジョウ"
    assert record["is_generic"] is False
    assert record["generic_name_label"] == "アスピリン錠100mg"
    assert "dict_enabled" not in record, "dict_enabledはupsertペイロードに含めてはならない"
