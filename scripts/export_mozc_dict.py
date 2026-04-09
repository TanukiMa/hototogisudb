"""Export Mozc system dictionary TSV from Supabase."""
import sys
from pathlib import Path

# Ensure local package path is first
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

import argparse
import logging
from mozc4med_dict.exporters.mozc_system_dict import MozcSystemDictExporter

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

def main() -> None:
    parser = argparse.ArgumentParser(description="Export Mozc system dictionary")
    parser.add_argument("--output", type=Path, default=Path("dist/mozc4med_medical.txt"))
    parser.add_argument("--no-skip", action="store_true", help="Do not skip entries with non‑kana characters")
    parser.add_argument("--dry-run", action="store_true", help="Count only, no file written")
    parser.add_argument("--include-invalid", action="store_true", help="Export all entries, ignoring normalization errors and NULL raw_reading. For debugging only.")

    args = parser.parse_args()
    exporter = MozcSystemDictExporter()
    written, skipped = exporter.export(
        output_path=args.output,
        dry_run=args.dry_run,
        no_skip=args.no_skip,
        include_invalid=args.include_invalid,
    )
    if args.dry_run:
        logging.info("Dry-run: %d entries would be exported", written)
    else:
        logging.info("Exported %d entries to %s (%d skipped)", written, args.output, skipped)


if __name__ == "__main__":
    main()
