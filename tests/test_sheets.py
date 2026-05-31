from __future__ import annotations

from unittest import TestCase

from plaid_sheet_sync.sheets import GoogleSheetsClient


class _Execute:
    def __init__(self, result=None):
        self.result = result or {}

    def execute(self):
        return self.result


class _Values:
    def __init__(self):
        self.append_calls = []

    def append(self, **kwargs):
        self.append_calls.append(kwargs)
        return _Execute({"updates": {"updatedRows": len(kwargs["body"]["values"])}})


class _Spreadsheets:
    def __init__(self):
        self.values_obj = _Values()

    def values(self):
        return self.values_obj


class _Service:
    def __init__(self):
        self.spreadsheets_obj = _Spreadsheets()

    def spreadsheets(self):
        return self.spreadsheets_obj


class SheetsTests(TestCase):
    def test_append_rows_uses_expected_range_and_body(self) -> None:
        client = object.__new__(GoogleSheetsClient)
        client.spreadsheet_id = "sheet-id"
        client.service = _Service()

        client.append_rows("balance_snapshots", [["a", "b"]])

        calls = client.service.spreadsheets_obj.values_obj.append_calls
        self.assertEqual(
            calls,
            [
                {
                    "spreadsheetId": "sheet-id",
                    "range": "balance_snapshots!A1",
                    "valueInputOption": "RAW",
                    "insertDataOption": "INSERT_ROWS",
                    "body": {"values": [["a", "b"]]},
                }
            ],
        )
