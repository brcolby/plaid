from __future__ import annotations

from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
from tempfile import TemporaryDirectory
from unittest import TestCase

from plaid_sheet_sync.state import StateStore
from plaid_sheet_sync.sync import run_sync


class SyncTests(TestCase):
    def test_sync_skips_holdings_for_depository_only_item(self) -> None:
        with TemporaryDirectory() as tmpdir:
            state = StateStore(Path(tmpdir) / "state.sqlite")
            state.upsert_item(
                item_id="item-1",
                access_token="redacted-token",
                institution_id="ins_1",
                institution_name="Bank",
            )
            plaid = _FakePlaid()

            with redirect_stdout(StringIO()):
                result = run_sync(state=state, plaid=plaid, sheets=None, dry_run=True)

        self.assertEqual(result.balance_rows, 1)
        self.assertEqual(result.holding_rows, 0)
        self.assertEqual(result.failure_count, 0)
        self.assertEqual(plaid.holdings_calls, 0)


class _FakePlaid:
    def __init__(self) -> None:
        self.holdings_calls = 0

    def get_balances(self, access_token: str) -> dict:
        return {
            "accounts": [
                {
                    "account_id": "account-1",
                    "name": "Savings",
                    "type": "depository",
                    "subtype": "savings",
                    "balances": {"current": 1.0, "available": 1.0, "iso_currency_code": "USD"},
                }
            ]
        }

    def get_holdings(self, access_token: str) -> dict:
        self.holdings_calls += 1
        raise AssertionError("holdings should not be called for depository accounts")
