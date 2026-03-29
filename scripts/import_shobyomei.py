"""Import SSK shobyomei master CSV into Supabase."""
import argparse
import logging
from pathlib import Path

from mozc4med_dict.importers.ssk_shobyomei import SskShobyomeiImporter

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import SSK shobyomei master")
    parser.add_argument("--file", required=True, type=Path, help="Path to b_ALL*.csv")
    parser.add_argument("--url", default=None, help="Source download URL")
    parser.add_argument("--imported-by", default=None, help="Username")
    parser.add_argument("--notes", default=None)
    args = parser.parse_args()

    importer = SskShobyomeiImporter()
    try:
        count = importer.run(
            file_path=args.file,
            source_url=args.url,
            imported_by=args.imported_by,
            notes=args.notes,
        )
        logging.info("Done: %d records imported", count)
    except ValueError as e:
        logging.error("%s", e)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
