"""Import custom terms CSV into Supabase."""
import argparse
import logging
from pathlib import Path

from mozc4med_dict.importers.csv_generic import CsvGenericImporter

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import custom terms CSV")
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--source", default=None, help="Source label")
    args = parser.parse_args()

    importer = CsvGenericImporter()
    count = importer.import_file(file_path=args.file, source_label=args.source)
    logging.info("Done: %d records imported", count)


if __name__ == "__main__":
    main()
