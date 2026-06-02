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

LIABILITY_HEADERS = [
    "polled_at",
    "institution_name",
    "institution_id",
    "account_name",
    "official_name",
    "account_type",
    "account_subtype",
    "account_id",
    "mask",
    "liability_type",
    "current_balance",
    "available_balance",
    "limit",
    "currency",
    "interest_rate_percentage",
    "interest_rate_type",
    "apr_summary",
    "next_payment_amount",
    "next_payment_due_date",
    "last_payment_amount",
    "last_payment_date",
    "last_statement_balance",
    "is_overdue",
    "loan_name",
    "loan_status",
    "repayment_plan",
    "origination_principal_amount",
    "origination_date",
    "expected_payoff_date",
    "guarantor",
    "ytd_interest_paid",
    "ytd_principal_paid",
    "plaid_item_id",
    "status",
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


def liability_rows(item: StoredItem, response: dict[str, Any], polled_at: str) -> list[list[Any]]:
    accounts = {account.get("account_id"): account for account in response.get("accounts", [])}
    liabilities = response.get("liabilities") or {}
    rows = []

    for liability_type in ("credit", "student", "mortgage"):
        for liability in liabilities.get(liability_type, []) or []:
            account = accounts.get(liability.get("account_id"), {})
            rows.append(_liability_row(item, account, liability_type, liability, polled_at))

    return rows


def _liability_row(
    item: StoredItem,
    account: dict[str, Any],
    liability_type: str,
    liability: dict[str, Any],
    polled_at: str,
) -> list[Any]:
    balances = account.get("balances") or {}
    interest_rate = liability.get("interest_rate") or {}
    return [
        polled_at,
        item.institution_name,
        item.institution_id,
        account.get("name"),
        account.get("official_name"),
        account.get("type"),
        account.get("subtype"),
        liability.get("account_id"),
        account.get("mask"),
        liability_type,
        balances.get("current"),
        balances.get("available"),
        balances.get("limit"),
        balances.get("iso_currency_code") or balances.get("unofficial_currency_code"),
        liability.get("interest_rate_percentage") or interest_rate.get("percentage"),
        interest_rate.get("type"),
        _apr_summary(liability.get("aprs")),
        _next_payment_amount(liability_type, liability),
        liability.get("next_payment_due_date"),
        liability.get("last_payment_amount"),
        liability.get("last_payment_date"),
        liability.get("last_statement_balance"),
        liability.get("is_overdue"),
        liability.get("loan_name"),
        _typed_description(liability.get("loan_status")),
        _typed_description(liability.get("repayment_plan")),
        liability.get("origination_principal_amount"),
        liability.get("origination_date"),
        liability.get("expected_payoff_date"),
        liability.get("guarantor"),
        liability.get("ytd_interest_paid"),
        liability.get("ytd_principal_paid"),
        item.item_id,
        "ok",
    ]


def _apr_summary(aprs: list[dict[str, Any]] | None) -> str | None:
    if not aprs:
        return None
    parts = []
    for apr in aprs:
        label = apr.get("apr_type") or "apr"
        percentage = apr.get("apr_percentage")
        balance = apr.get("balance_subject_to_apr")
        interest = apr.get("interest_charge_amount")
        details = [f"{label}:{percentage}%" if percentage is not None else str(label)]
        if balance is not None:
            details.append(f"balance={balance}")
        if interest is not None:
            details.append(f"interest={interest}")
        parts.append(" ".join(details))
    return "; ".join(parts)


def _next_payment_amount(liability_type: str, liability: dict[str, Any]) -> Any:
    if liability_type == "mortgage":
        return liability.get("next_monthly_payment")
    return liability.get("minimum_payment_amount")


def _typed_description(value: dict[str, Any] | None) -> str | None:
    if not value:
        return None
    kind = value.get("type")
    description = value.get("description")
    if kind and description:
        return f"{kind}: {description}"
    return kind or description
