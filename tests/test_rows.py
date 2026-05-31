from __future__ import annotations

from unittest import TestCase

from plaid_sheet_sync.rows import BALANCE_HEADERS, HOLDING_HEADERS, balance_rows, holding_rows
from plaid_sheet_sync.state import StoredItem


class RowMappingTests(TestCase):
    def test_balance_rows_maps_accounts(self) -> None:
        item = _item()
        response = {
            "accounts": [
                {
                    "account_id": "acc-1",
                    "name": "Checking",
                    "official_name": "Everyday Checking",
                    "type": "depository",
                    "subtype": "checking",
                    "mask": "1234",
                    "balances": {
                        "current": 100.25,
                        "available": 90.25,
                        "limit": None,
                        "iso_currency_code": "USD",
                    },
                }
            ]
        }

        rows = balance_rows(item, response, "2026-05-31T12:00:00+00:00")

        self.assertEqual(len(rows), 1)
        row = dict(zip(BALANCE_HEADERS, rows[0], strict=True))
        self.assertEqual(row["institution_name"], "Wells Fargo")
        self.assertEqual(row["account_name"], "Checking")
        self.assertEqual(row["current_balance"], 100.25)
        self.assertEqual(row["status"], "ok")

    def test_holding_rows_maps_security_and_account(self) -> None:
        item = _item()
        response = {
            "accounts": [
                {
                    "account_id": "acc-2",
                    "name": "401k",
                    "type": "investment",
                    "subtype": "401k",
                }
            ],
            "securities": [
                {
                    "security_id": "sec-1",
                    "name": "Total Market Fund",
                    "ticker_symbol": "VTI",
                    "type": "etf",
                    "iso_currency_code": "USD",
                }
            ],
            "holdings": [
                {
                    "account_id": "acc-2",
                    "security_id": "sec-1",
                    "quantity": 3.5,
                    "institution_price": 250.0,
                    "institution_value": 875.0,
                }
            ],
        }

        rows = holding_rows(item, response, "2026-05-31T12:00:00+00:00")

        self.assertEqual(len(rows), 1)
        row = dict(zip(HOLDING_HEADERS, rows[0], strict=True))
        self.assertEqual(row["account_name"], "401k")
        self.assertEqual(row["ticker_symbol"], "VTI")
        self.assertEqual(row["value"], 875.0)
        self.assertEqual(row["currency"], "USD")


def _item() -> StoredItem:
    return StoredItem(
        item_id="item-1",
        access_token="redacted-token",
        institution_id="ins_1",
        institution_name="Wells Fargo",
        created_at="2026-05-31T12:00:00+00:00",
        updated_at="2026-05-31T12:00:00+00:00",
        last_success_at=None,
        last_error=None,
        metadata={},
    )
