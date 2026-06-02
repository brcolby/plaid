from __future__ import annotations

from unittest import TestCase

from plaid_sheet_sync.rows import (
    BALANCE_HEADERS,
    HOLDING_HEADERS,
    LIABILITY_HEADERS,
    balance_rows,
    holding_rows,
    liability_rows,
)
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

    def test_liability_rows_maps_credit_and_student_debts(self) -> None:
        item = _item()
        response = {
            "accounts": [
                {
                    "account_id": "credit-1",
                    "name": "Credit Card",
                    "type": "credit",
                    "subtype": "credit card",
                    "mask": "2222",
                    "balances": {
                        "current": 1200.0,
                        "available": 3800.0,
                        "limit": 5000.0,
                        "iso_currency_code": "USD",
                    },
                },
                {
                    "account_id": "student-1",
                    "name": "Student Loan",
                    "type": "loan",
                    "subtype": "student",
                    "balances": {"current": 9500.0, "iso_currency_code": "USD"},
                },
            ],
            "liabilities": {
                "credit": [
                    {
                        "account_id": "credit-1",
                        "aprs": [
                            {
                                "apr_type": "purchase_apr",
                                "apr_percentage": 21.24,
                                "balance_subject_to_apr": 1200.0,
                                "interest_charge_amount": 12.5,
                            }
                        ],
                        "minimum_payment_amount": 35.0,
                        "next_payment_due_date": "2026-06-20",
                        "last_statement_balance": 1100.0,
                        "is_overdue": False,
                    }
                ],
                "student": [
                    {
                        "account_id": "student-1",
                        "interest_rate_percentage": 4.75,
                        "minimum_payment_amount": 125.0,
                        "next_payment_due_date": "2026-06-15",
                        "loan_name": "Direct Loan",
                        "loan_status": {"type": "repayment", "description": "In repayment"},
                        "repayment_plan": {"type": "standard", "description": "Standard"},
                        "origination_principal_amount": 10000.0,
                        "ytd_interest_paid": 50.0,
                        "ytd_principal_paid": 250.0,
                    }
                ],
            },
        }

        rows = liability_rows(item, response, "2026-05-31T12:00:00+00:00")

        self.assertEqual(len(rows), 2)
        credit = dict(zip(LIABILITY_HEADERS, rows[0], strict=True))
        student = dict(zip(LIABILITY_HEADERS, rows[1], strict=True))
        self.assertEqual(credit["liability_type"], "credit")
        self.assertEqual(credit["current_balance"], 1200.0)
        self.assertIn("purchase_apr:21.24%", credit["apr_summary"])
        self.assertEqual(credit["next_payment_amount"], 35.0)
        self.assertEqual(student["liability_type"], "student")
        self.assertEqual(student["interest_rate_percentage"], 4.75)
        self.assertEqual(student["loan_status"], "repayment: In repayment")


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
