"""URL resolution and ZIP extraction for SSK master CSV files."""
import shutil
import tempfile
import zipfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from urllib.error import URLError
from urllib.parse import unquote, urlparse
from urllib.request import urlretrieve


class DownloadError(Exception):
    """Raised when a download or extraction fails."""


def _url_to_local_path(url: str) -> Path:
    """Convert a file:// URL to a local Path, handling Windows drive letters."""
    parsed = urlparse(url)
    path_str = unquote(parsed.path)
    # Windows: file:///C:/foo → /C:/foo → C:/foo
    if len(path_str) >= 3 and path_str[0] == "/" and path_str[2] == ":":
        path_str = path_str[1:]
    return Path(path_str)


@contextmanager
def resolve_csv(url: str, csv_glob: str = "*.csv") -> Generator[Path, None, None]:
    """Resolve URL → local CSV path. Cleans up temp files on exit.

    Supported schemes:
      - https:// / http:// → download ZIP, extract matching CSV
      - file:// (ZIP)      → extract matching CSV to temp dir
      - file:// (CSV)      → yield path directly (no temp dir)

    Raises:
        DownloadError:     Network error, invalid ZIP, or no matching CSV found
        FileNotFoundError: file:// target does not exist
        ValueError:        Unsupported scheme or file extension
    """
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme in ("https", "http"):
        tmp_dir = Path(tempfile.mkdtemp())
        try:
            zip_path = tmp_dir / "master.zip"
            try:
                urlretrieve(url, zip_path)  # noqa: S310
            except URLError as e:
                raise DownloadError(f"Failed to download {url}: {e}") from e
            yield from _extract_csv(zip_path, tmp_dir, csv_glob)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    elif scheme == "file":
        local_path = _url_to_local_path(url)
        if not local_path.exists():
            raise FileNotFoundError(f"File not found: {local_path}")
        suffix = local_path.suffix.lower()
        if suffix == ".zip":
            tmp_dir = Path(tempfile.mkdtemp())
            try:
                yield from _extract_csv(local_path, tmp_dir, csv_glob)
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)
        elif suffix == ".csv":
            yield local_path
        else:
            raise ValueError(f"Unsupported file extension: {suffix} (expected .zip or .csv)")

    else:
        raise ValueError(f"Unsupported URL scheme: {scheme!r} (expected https, http, or file)")


def _extract_csv(zip_path: Path, extract_dir: Path, csv_glob: str) -> Generator[Path, None, None]:
    """Extract ZIP and yield the matching CSV file path."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)
    except zipfile.BadZipFile as e:
        raise DownloadError(f"Invalid ZIP file {zip_path.name}: {e}") from e

    matches = list(extract_dir.glob(csv_glob))
    if not matches:
        raise DownloadError(f"No file matching {csv_glob!r} found in {zip_path.name}")
    if len(matches) > 1:
        names = ", ".join(sorted(path.name for path in matches))
        raise DownloadError(
            f"Multiple files matching {csv_glob!r} found in {zip_path.name}: {names}"
        )
    yield matches[0]
