from unittest.mock import MagicMock, patch

from mozc4med_dict.importers.ssk_shinryo_koi import SskShinryoKoiImporter


def test_ssk_shinryo_koi_parse_row(tmp_path):
    fields = [""] * 113
    fields[0] = "1"
    fields[2] = "123456789"
    fields[4] = "初診料"
    fields[6] = "ショシンリョウ"
    fields[86] = "20200401"
    fields[87] = ""
    fields[112] = "初診料（基本）"

    line = ",".join(fields).encode("cp932")
    csv_file = tmp_path / "s_test.csv"
    csv_file.write_bytes(line + b"\r\n")

    mock_client = MagicMock()
    t = mock_client.table.return_value
    t.select.return_value.eq.return_value.execute.return_value.data = []
    t.insert.return_value.execute.return_value.data = [{"id": 99}]
    t.update.return_value.eq.return_value.execute.return_value.data = []
    mock_client.rpc.return_value.execute.return_value.data = [{}]

    with patch("mozc4med_dict.importers.base.get_client", return_value=mock_client):
        importer = SskShinryoKoiImporter()
        count = importer.run(file_path=csv_file, imported_by="test")

    assert count == 1
    rpc_call = mock_client.rpc.call_args
    assert rpc_call[0][0] == "upsert_ssk_shinryo_koi"
    record = rpc_call[0][1]["records"][0]
    assert record["shinryo_koi_code"] == "123456789"
    assert record["abbr_kanji_name"] == "初診料"
    # 正規化は行わず、生データがそのまま保存される
    assert record["abbr_kana_name"] == "ショシンリョウ"
    assert record["base_kanji_name"] == "初診料（基本）"
    assert record["is_active"] is True
    assert "dict_enabled" not in record, "dict_enabledはupsertペイロードに含めてはならない"
