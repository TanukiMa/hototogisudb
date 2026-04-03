from unittest.mock import MagicMock, patch

from mozc4med_dict.importers.csv_generic import CsvGenericImporter


def test_csv_generic_importer(tmp_path):
    csv_content = "surface_form,reading,cost,pos_type_id,source_label,source_url,notes\n"
    csv_content += "糖尿病手帳,とうにょうびょうてちょう,4800,,Custom v1,,\n"
    csv_file = tmp_path / "custom.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    mock_client = MagicMock()

    with patch("mozc4med_dict.importers.csv_generic.get_client", return_value=mock_client):
        importer = CsvGenericImporter()
        count = importer.import_file(file_path=csv_file, source_label="Custom v1")

    assert count == 1
    call_kwargs = mock_client.rpc.call_args
    assert call_kwargs[0][0] == "upsert_custom_terms"
    record = call_kwargs[0][1]["records"][0]
    assert record["surface_form"] == "糖尿病手帳"
    assert record["reading"] == "とうにょうびょうてちょう"
    assert record["cost"] == 4800
    assert "dict_enabled" not in record, "dict_enabledはupsertペイロードに含めてはならない"
