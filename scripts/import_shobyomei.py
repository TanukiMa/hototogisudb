"""Import SSK shobyomei master CSV into Supabase."""
import argparse
import logging
import sys

from mozc4med_dict.importers.ssk_shobyomei import SskShobyomeiImporter
from mozc4med_dict.utils.download import DownloadError, resolve_csv

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import SSK shobyomei master")
    parser.add_argument("--url", required=True, help="https:// or file:// URL to ZIP or CSV")
    parser.add_argument("--imported-by", default=None)
    parser.add_argument("--notes", default=None)
    args = parser.parse_args()

    try:
        with resolve_csv(args.url, csv_glob="b_*.txt") as csv_path:
            importer = SskShobyomeiImporter()
            count = importer.run(
                file_path=csv_path,
                source_url=args.url,
                imported_by=args.imported_by,
                notes=args.notes,
            )
        logging.info("Done: %d records imported", count)
    except (DownloadError, FileNotFoundError, ValueError) as e:
        logging.error("%s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
