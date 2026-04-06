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

_TABLE_ARG_TO_NAME = {
    "iyakuhin": "ssk_iyakuhin",
    "shinryo_koi": "ssk_shinryo_koi",
}


def _rows_from_response(data: object, *, context: str) -> list[dict[str, object]]:
    if data is None:
        return []
    if not isinstance(data, list):
        raise ValueError(f"{context} returned unexpected payload type: {type(data).__name__}")

    rows: list[dict[str, object]] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"{context} row[{index}] is not an object")
        rows.append(item)
    return rows


def _resolve_target_table(code: str, table: str | None) -> str:
    if not code.isdigit():
        raise ValueError("CODE must be numeric.")
    if len(code) == 7:
        if table is not None:
            raise ValueError("--table must not be set for 7-digit codes.")
        return "ssk_shobyomei"
    if len(code) == 9:
        if table is None:
            raise ValueError("--table is required for 9-digit codes (shinryo_koi or iyakuhin).")
        return _TABLE_ARG_TO_NAME[table]
    raise ValueError("CODE must be 7 or 9 digits.")


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
        rows = _rows_from_response(res.data, context=f"{table} list abolished")
        for row in sorted(rows, key=lambda x: str(x.get(code_col, ""))):
            print(f"{table}\t{row.get(code_col)}\tabolished but dict_enabled=TRUE")


def set_term_enabled(code: str, *, table: str | None, enabled: bool) -> None:
    client = get_client()
    target_table = _resolve_target_table(code, table)
    code_col = _TABLES[target_table]

    res = (
        client.table(target_table)
        .update({"dict_enabled": enabled})
        .eq(code_col, code)
        .execute()
    )
    rows = _rows_from_response(res.data, context=f"{target_table} update")
    if rows:
        action = "Enabled" if enabled else "Disabled"
        logging.info("%s %s in %s", action, code, target_table)
    else:
        logging.warning("Code %s not found in %s", code, target_table)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage dict_enabled flags")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list-abolished", action="store_true")
    group.add_argument("--disable", metavar="CODE")
    group.add_argument("--enable", metavar="CODE")
    parser.add_argument(
        "--table",
        choices=sorted(_TABLE_ARG_TO_NAME.keys()),
        default=None,
        help="Required for 9-digit codes: shinryo_koi or iyakuhin",
    )
    args = parser.parse_args()

    if args.list_abolished:
        if args.table is not None:
            parser.error("--table can only be used with --disable or --enable")
        list_abolished()
    elif args.disable:
        try:
            set_term_enabled(args.disable, table=args.table, enabled=False)
        except ValueError as e:
            parser.error(str(e))
    elif args.enable:
        try:
            set_term_enabled(args.enable, table=args.table, enabled=True)
        except ValueError as e:
            parser.error(str(e))


if __name__ == "__main__":
    main()
