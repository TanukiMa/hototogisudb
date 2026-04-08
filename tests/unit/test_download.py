import zipfile

import pytest

from mozc4med_dict.utils.download import DownloadError, resolve_csv


def test_resolve_csv_decodes_percent_encoded_file_path(tmp_path):
    csv_path = tmp_path / "a b.csv"
    csv_path.write_text("x\n", encoding="utf-8")

    with resolve_csv(csv_path.as_uri()) as resolved_path:
        assert resolved_path == csv_path


def test_resolve_csv_raises_when_multiple_csv_match(tmp_path):
    zip_path = tmp_path / "multi.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("a.csv", "x\n")
        zf.writestr("b.csv", "y\n")

    with pytest.raises(DownloadError, match="Multiple files matching"):
        with resolve_csv(zip_path.as_uri(), csv_glob="*.csv"):
            pass
