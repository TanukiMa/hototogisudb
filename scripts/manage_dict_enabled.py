"""Inspect or toggle dict_enabled flags across SSK master tables."""
import argparse
import logging

from mozc4med_dict.db import get_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

_TABLES = {
    "ssk_shobyomei": "shobyomei_code",
    "ssk_iyakuhin": "iyakuhin_code",
    "ssk_shinryo_koi": "shinryo_koi_code",
}


def list_abolished() -> None:
    client = get_client()
    for table, code_col in _TABLES.items():
        res = (
            client.table(table)
            .select(f"{code_col},dict_enabled,is_active")
            .eq("is_active", False)
            .eq("dict_enabled", True)
            .execute()
        )
        for row in res.data:
            print(f"{table}\t{row[code_col]}\tabolished but dict_enabled=TRUE")


def disable_term(code: str) -> None:
    client = get_client()
    found = False
    for table, code_col in _TABLES.items():
        res = (
            client.table(table)
            .update({"dict_enabled": False})
            .eq(code_col, code)
            .execute()
        )
        if res.data:
            logging.info("Disabled %s in %s", code, table)
            found = True
    if not found:
        logging.warning("Code %s not found in any table", code)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage dict_enabled flags")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list-abolished", action="store_true")
    group.add_argument("--disable", metavar="CODE")
    args = parser.parse_args()

    if args.list_abolished:
        list_abolished()
    elif args.disable:
        disable_term(args.disable)


if __name__ == "__main__":
    main()
