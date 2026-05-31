from __future__ import annotations

import argparse
import sys

from .config import ConfigError, load_config, require_plaid, require_sheets
from .link_server import LinkServer
from .plaid_client import PlaidDependencyError, PlaidService
from .sheets import GoogleSheetsClient, SheetsDependencyError
from .state import StateStore
from .sync import run_sync


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "link":
            return _link(args)
        if args.command == "sync":
            return _sync(args)
        if args.command == "list":
            return _list(args)
    except (ConfigError, PlaidDependencyError, SheetsDependencyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130

    parser.print_help()
    return 2


def _build_parser() -> argparse.ArgumentParser:
    env_parent = argparse.ArgumentParser(add_help=False)
    env_parent.add_argument("--env-file", default=".env", help="Path to local env file.")

    parser = argparse.ArgumentParser(prog="plaid-sheet-sync", parents=[env_parent])
    subparsers = parser.add_subparsers(dest="command", required=True)

    link = subparsers.add_parser(
        "link",
        help="Run a local Plaid Link flow.",
        parents=[env_parent],
    )
    link.add_argument("--host", default="127.0.0.1")
    link.add_argument("--port", type=int, default=8080)
    link.add_argument("--no-browser", action="store_true")
    link.add_argument(
        "--products",
        help="Comma-separated Plaid Link products for this institution, e.g. auth or investments.",
    )

    sync = subparsers.add_parser(
        "sync",
        help="Poll Plaid and append rows to Google Sheets.",
        parents=[env_parent],
    )
    sync.add_argument("--dry-run", action="store_true", help="Print rows without writing Sheets.")
    sync.add_argument("--skip-holdings", action="store_true", help="Only poll account balances.")

    subparsers.add_parser(
        "list",
        help="List linked Items and cached accounts without tokens.",
        parents=[env_parent],
    )
    return parser


def _link(args: argparse.Namespace) -> int:
    config = load_config(args.env_file)
    require_plaid(config)
    state = StateStore(config.state_db)
    plaid = PlaidService(config)
    LinkServer(
        plaid=plaid,
        state=state,
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
        products=_parse_products(args.products) if args.products else config.plaid_link_products,
    ).run()
    return 0


def _sync(args: argparse.Namespace) -> int:
    config = load_config(args.env_file)
    require_plaid(config)
    if not args.dry_run:
        require_sheets(config)
    state = StateStore(config.state_db)
    plaid = PlaidService(config)
    sheets = None if args.dry_run else GoogleSheetsClient(config)
    result = run_sync(
        state=state,
        plaid=plaid,
        sheets=sheets,
        dry_run=args.dry_run,
        skip_holdings=args.skip_holdings,
    )
    print(
        "sync complete: "
        f"{result.balance_rows} balance rows, "
        f"{result.holding_rows} holding rows, "
        f"{result.success_count} successes, "
        f"{result.failure_count} failures"
    )
    if result.errors:
        print("errors:")
        for error in result.errors:
            print(f"- {error}")
    return 0 if result.success_count or not result.failure_count else 1


def _list(args: argparse.Namespace) -> int:
    config = load_config(args.env_file)
    state = StateStore(config.state_db)
    items = state.list_items()
    accounts = state.list_accounts()
    accounts_by_item: dict[str, list[dict[str, str]]] = {}
    for account in accounts:
        accounts_by_item.setdefault(account["item_id"], []).append(account)

    if not items:
        print("No linked Items found.")
        return 0

    for item in items:
        label = item.institution_name or item.institution_id or item.item_id
        print(f"{label} ({item.item_id})")
        if item.last_success_at:
            print(f"  last success: {item.last_success_at}")
        if item.last_error:
            print(f"  last error: {item.last_error}")
        for account in accounts_by_item.get(item.item_id, []):
            name = account.get("name") or account["account_id"]
            subtype = account.get("subtype") or account.get("type") or "account"
            mask = f" ...{account['mask']}" if account.get("mask") else ""
            print(f"  - {name} ({subtype}){mask}")
    return 0


def _parse_products(value: str) -> tuple[str, ...]:
    products = tuple(part.strip().lower() for part in value.split(",") if part.strip())
    if not products:
        raise ConfigError("--products must contain at least one Plaid product")
    return products


if __name__ == "__main__":
    raise SystemExit(main())
