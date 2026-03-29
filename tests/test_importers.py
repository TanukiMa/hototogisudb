import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mozc4med_dict.utils.kana import normalize_reading


def test_normalize_reading_katakana_to_hiragana():
    assert normalize_reading("トウニョウビョウ") == "とうにょうびょう"


def test_normalize_reading_already_hiragana():
    assert normalize_reading("とうにょうびょう") == "とうにょうびょう"


def test_normalize_reading_strips_whitespace():
    assert normalize_reading("　アスピリン　") == "あすぴりん"


def test_normalize_reading_empty():
    assert normalize_reading("") == ""


def test_normalize_reading_mixed():
    assert normalize_reading("インスリンチュウシャ") == "いんすりんちゅうしゃ"


# BaseImporter tests


def test_base_importer_duplicate_detection(tmp_path):
    """Test that BaseImporter raises ValueError on duplicate import."""
    from mozc4med_dict.importers.base import BaseImporter

    class ConcreteImporter(BaseImporter):
        source_type = "test_source"

        def _parse_rows(self, file_path: Path, batch_id: int) -> list[dict]:
            return [{"key": "value"}]

        def _upsert_rows(self, rows: list[dict]) -> int:
            return len(rows)

    csv_file = tmp_path / "test.csv"
    csv_file.write_bytes(b"dummy content")
    sha256 = hashlib.sha256(b"dummy content").hexdigest()

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": 1, "file_sha256": sha256}
    ]

    with patch("mozc4med_dict.importers.base.get_client", return_value=mock_client):
        importer = ConcreteImporter()
        with pytest.raises(ValueError, match="already imported"):
            importer.run(file_path=csv_file, source_url="http://example.com", imported_by="test")


def test_ssk_shobyomei_parse_row(tmp_path):
    from mozc4med_dict.importers.ssk_shobyomei import SskShobyomeiImporter

    fields = [""] * 24
    fields[0] = "1"           # change_type
    fields[2] = "1234567"     # shobyomei_code
    fields[3] = ""            # successor_code
    fields[5] = "糖尿病"      # base_name
    fields[7] = "DM"          # abbr_name
    fields[9] = "トウニョウビョウ"  # kana_name
    fields[10] = "12345678"   # byomei_mgmt_code
    fields[11] = "1"          # adoption_type
    fields[15] = "E11"        # icd10_1
    fields[16] = ""           # icd10_2
    fields[21] = "20200101"   # listed_at
    fields[22] = ""           # changed_at
    fields[23] = ""           # abolished_at

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
    assert record["dict_enabled"] is True
