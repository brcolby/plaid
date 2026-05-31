from __future__ import annotations

from typing import Any

from .state import StoredItem


BALANCE_HEADERS = [
    "polled_at",
    "institution_name",
    "institution_id",
    "account_name",
    "official_name",
    "account_type",
    "account_subtype",
    "account_id",
    "mask",
    "current_balance",
    "available_balance",
    "limit",
    "currency",
    "plaid_item_id",
    "status",
]

HOLDING_HEADERS = [
    "polled_at",
    "institution_name",
    "institution_id",
    "account_name",
    "account_type",
    "account_subtype",
    "account_id",
    "security_name",
    "ticker_symbol",
    "security_type",
    "security_id",
    "quantity",
    "price",
    "value",
    "currency",
    "plaid_item_id",
]

SYNC_RUN_HEADERS = [
    "started_at",
    "ended_at",
    "duration_ms",
    "items_total",
    "balance_rows",
    "holding_rows",
    "success_count",
    "failure_count",
    "error_summary",
]


def balance_rows(item: StoredItem, response: dict[str, Any], polled_at: str) -> list[list[Any]]:
    rows = []
    for account in response.get("accounts", []):
        balances = account.get("balances") or {}
        rows.append(
            [
                polled_at,
                item.institution_name,
                item.institution_id,
                account.get("name"),
                account.get("official_name"),
                account.get("type"),
                account.get("subtype"),
                account.get("account_id"),
                account.get("mask"),
                balances.get("current"),
                balances.get("available"),
                balances.get("limit"),
                balances.get("iso_currency_code") or balances.get("unofficial_currency_code"),
                item.item_id,
                "ok",
            ]
        )
    return rows


def holding_rows(item: StoredItem, response: dict[str, Any], polled_at: str) -> list[list[Any]]:
    accounts = {account.get("account_id"): account for account in response.get("accounts", [])}
    securities = {security.get("security_id"): security for security in response.get("securities", [])}

    rows = []
    for holding in response.get("holdings", []):
        account = accounts.get(holding.get("account_id"), {})
        security = securities.get(holding.get("security_id"), {})
        rows.append(
            [
                polled_at,
                item.institution_name,
                item.institution_id,
                account.get("name"),
                account.get("type"),
                account.get("subtype"),
                holding.get("account_id"),
                security.get("name"),
                security.get("ticker_symbol"),
                security.get("type"),
                holding.get("security_id"),
                holding.get("quantity"),
                holding.get("institution_price"),
                holding.get("institution_value"),
                holding.get("iso_currency_code")
                or security.get("iso_currency_code")
                or holding.get("unofficial_currency_code")
                or security.get("unofficial_currency_code"),
                item.item_id,
            ]
        )
    return rows

