from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import urllib3

from plaid_sheet_sync.plaid_client import PlaidService


class PlaidServiceTests(TestCase):
    def test_call_with_retries_passes_timeout_and_retries_transport_error(self) -> None:
        service = PlaidService.__new__(PlaidService)
        service.config = SimpleNamespace(plaid_request_timeout_seconds=12.5, plaid_max_retries=1)
        calls = []

        def fake_call(request: object, **kwargs: object) -> dict[str, str]:
            calls.append(kwargs)
            if len(calls) == 1:
                raise urllib3.exceptions.ProtocolError("connection reset")
            return {"ok": "yes"}

        with patch("plaid_sheet_sync.plaid_client.time.sleep") as sleep:
            result = service._call_with_retries(fake_call, object())

        self.assertEqual(result, {"ok": "yes"})
        self.assertEqual(calls, [{"_request_timeout": 12.5}, {"_request_timeout": 12.5}])
        sleep.assert_called_once_with(1)

    def test_call_with_retries_does_not_retry_non_retryable_error(self) -> None:
        service = PlaidService.__new__(PlaidService)
        service.config = SimpleNamespace(plaid_request_timeout_seconds=12.5, plaid_max_retries=2)

        with self.assertRaises(ValueError), patch("plaid_sheet_sync.plaid_client.time.sleep") as sleep:
            service._call_with_retries(_raise_value_error, object())

        sleep.assert_not_called()


def _raise_value_error(request: object, **kwargs: object) -> object:
    raise ValueError("bad request")
