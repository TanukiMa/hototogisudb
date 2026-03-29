from pathlib import Path
from unittest.mock import MagicMock, patch

from mozc4med_dict.exporters.mozc_system_dict import MozcSystemDictExporter


def test_exporter_generates_tsv(tmp_path):
    mock_data = [
        {
            "reading": "とうにょうびょう",
            "left_id": 1849,
            "right_id": 1849,
            "cost": 4800,
            "surface_form": "糖尿病",
        },
        {
            "reading": "あすぴりん",
            "left_id": 1849,
            "right_id": 1849,
            "cost": 5000,
            "surface_form": "アスピリン",
        },
    ]

    mock_client = MagicMock()
    mock_client.rpc.return_value.execute.return_value.data = mock_data

    out_file = tmp_path / "out.txt"

    with patch("mozc4med_dict.exporters.mozc_system_dict.get_client", return_value=mock_client):
        exporter = MozcSystemDictExporter()
        count = exporter.export(output_path=out_file)

    assert count == 2
    lines = out_file.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "とうにょうびょう\t1849\t1849\t4800\t糖尿病"
    assert lines[1] == "あすぴりん\t1849\t1849\t5000\tアスピリン"


def test_exporter_dry_run(tmp_path):
    mock_data = [
        {
            "reading": "とうにょうびょう",
            "left_id": 1849,
            "right_id": 1849,
            "cost": 4800,
            "surface_form": "糖尿病",
        }
    ]

    mock_client = MagicMock()
    mock_client.rpc.return_value.execute.return_value.data = mock_data

    out_file = tmp_path / "out.txt"

    with patch("mozc4med_dict.exporters.mozc_system_dict.get_client", return_value=mock_client):
        exporter = MozcSystemDictExporter()
        count = exporter.export(output_path=out_file, dry_run=True)

    assert count == 1
    assert not out_file.exists()
