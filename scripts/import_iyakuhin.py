"""Import SSK iyakuhin master CSV into Supabase."""
import argparse
import logging
from pathlib import Path

from mozc4med_dict.importers.ssk_iyakuhin import SskIyakuhinImporter

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import SSK iyakuhin master")
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--url", default=None)
    parser.add_argument("--imported-by", default=None)
    parser.add_argument("--notes", default=None)
    args = parser.parse_args()

    importer = SskIyakuhinImporter()
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
