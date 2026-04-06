import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mozc4med_dict.importers.base import BaseImporter


class ConcreteImporter(BaseImporter):
    source_type = "test_source"

    def _parse(self, file_path: Path) -> list[dict]:
        return [{"key": "value"}]


def test_base_importer_duplicate_detection(tmp_path):
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


def test_base_importer_sha256_method_alias(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_bytes(b"dummy content")
    expected = hashlib.sha256(b"dummy content").hexdigest()

    importer = ConcreteImporter()
    assert importer._sha256(csv_file) == expected
    assert importer._compute_sha256(csv_file) == expected
