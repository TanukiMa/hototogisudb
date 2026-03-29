from pathlib import Path
from unittest.mock import MagicMock, patch

from mozc4med_dict.importers.ssk_shobyomei import SskShobyomeiImporter


def test_ssk_shobyomei_parse_row(tmp_path):
    fields = [""] * 24
    fields[0] = "1"
    fields[2] = "1234567"
    fields[3] = ""
    fields[5] = "糖尿病"
    fields[7] = "DM"
    fields[9] = "トウニョウビョウ"
    fields[10] = "12345678"
    fields[11] = "1"
    fields[15] = "E11"
    fields[16] = ""
    fields[21] = "20200101"
    fields[22] = ""
    fields[23] = ""

    line = ",".join(fields).encode("cp932")
    csv_file = tmp_path / "b_test.csv"
    csv_file.write_bytes(line + b"\r\n")

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [{"id": 42}]
    mock_client.table.return_value.upsert.return_value.execute.return_value.data = [{}]
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

    with patch("mozc4med_dict.importers.base.get_client", return_value=mock_client):
        with patch("mozc4med_dict.importers.ssk_shobyomei.get_client", return_value=mock_client):
            importer = SskShobyomeiImporter()
            count = importer.run(
                file_path=csv_file,
                source_url="http://example.com",
                imported_by="test",
            )

    assert count == 1
    upsert_call = mock_client.table.return_value.upsert.call_args
    record = upsert_call[0][0][0]
    assert record["shobyomei_code"] == "1234567"
    assert record["base_name"] == "糖尿病"
    assert record["kana_name"] == "トウニョウビョウ"
    assert record["is_active"] is True
