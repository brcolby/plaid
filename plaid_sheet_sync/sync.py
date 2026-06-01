from __future__ import annotations

import json
import time
from dataclasses import dataclass

from .plaid_client import PlaidService
from .rows import BALANCE_HEADERS, HOLDING_HEADERS, SYNC_RUN_HEADERS, balance_rows, holding_rows
from .sheets import GoogleSheetsClient
from .state import StateStore, utc_now


SHEET_HEADERS = {
    "current_balances": BALANCE_HEADERS,
    "balance_snapshots": BALANCE_HEADERS,
    "holding_snapshots": HOLDING_HEADERS,
    "sync_runs": SYNC_RUN_HEADERS,
}


@dataclass(frozen=True)
class SyncResult:
    balance_rows: int
    holding_rows: int
    success_count: int
    failure_count: int
    errors: list[str]


def run_sync(
    *,
    state: StateStore,
    plaid: PlaidService,
    sheets: GoogleSheetsClient | None,
    dry_run: bool,
    skip_holdings: bool = False,
) -> SyncResult:
    started_at = utc_now()
    start_time = time.monotonic()
    items = state.list_items()
    all_balance_rows = []
    all_holding_rows = []
    errors: list[str] = []
    success_count = 0
    failure_count = 0

    for item in items:
        item_ok = False
        polled_at = utc_now()
        try:
            balance_response = plaid.get_balances(item.access_token)
            accounts = balance_response.get("accounts", [])
            state.upsert_accounts(item.item_id, accounts)
            rows = balance_rows(item, balance_response, polled_at)
            all_balance_rows.extend(rows)
            success_count += 1
            item_ok = True
        except Exception as exc:  # noqa: BLE001 - keep scheduled runs alive per Item.
            failure_count += 1
            errors.append(f"{item.institution_name or item.item_id} balances: {exc}")

        if not skip_holdings and _has_investment_account(balance_response if item_ok else None):
            try:
                holding_response = plaid.get_holdings(item.access_token)
                accounts = holding_response.get("accounts", [])
                state.upsert_accounts(item.item_id, accounts)
                rows = holding_rows(item, holding_response, polled_at)
                all_holding_rows.extend(rows)
                success_count += 1
                item_ok = True
            except Exception as exc:  # noqa: BLE001 - unsupported holdings are non-fatal.
                failure_count += 1
                errors.append(f"{item.institution_name or item.item_id} holdings: {exc}")

        state.mark_item_result(
            item.item_id,
            success=item_ok,
            error=None if item_ok else "; ".join(errors[-2:]),
        )

    ended_at = utc_now()
    duration_ms = int((time.monotonic() - start_time) * 1000)
    sync_run_row = [
        started_at,
        ended_at,
        duration_ms,
        len(items),
        len(all_balance_rows),
        len(all_holding_rows),
        success_count,
        failure_count,
        "; ".join(errors),
    ]

    if dry_run:
        print(
            json.dumps(
                {
                    "current_balances": [BALANCE_HEADERS, *all_balance_rows],
                    "balance_snapshots": [BALANCE_HEADERS, *all_balance_rows],
                    "holding_snapshots": [HOLDING_HEADERS, *all_holding_rows],
                    "sync_runs": [SYNC_RUN_HEADERS, sync_run_row],
                },
                indent=2,
                default=str,
            )
        )
    else:
        if sheets is None:
            raise ValueError("sheets client is required unless dry_run=True")
        sheets.ensure_tabs(SHEET_HEADERS)
        sheets.replace_rows("current_balances", BALANCE_HEADERS, all_balance_rows)
        sheets.append_rows("balance_snapshots", all_balance_rows)
        sheets.append_rows("holding_snapshots", all_holding_rows)
        sheets.append_rows("sync_runs", [sync_run_row])

    return SyncResult(
        balance_rows=len(all_balance_rows),
        holding_rows=len(all_holding_rows),
        success_count=success_count,
        failure_count=failure_count,
        errors=errors,
    )


def _has_investment_account(balance_response: dict | None) -> bool:
    if not balance_response:
        return False
    return any(account.get("type") == "investment" for account in balance_response.get("accounts", []))
