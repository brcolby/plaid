from __future__ import annotations

from pathlib import Path
import re
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from plaid_sheet_sync.config import ConfigError, load_config, require_plaid


class ConfigTests(TestCase):
    def test_load_config_reads_env_file(self) -> None:
        with TemporaryDirectory() as tmpdir, patch.dict("os.environ", {}, clear=True):
            env_file = Path(tmpdir) / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "PLAID_CLIENT_ID=client",
                        "PLAID_SECRET='secret'",
                        "PLAID_ENV=production",
                        "GOOGLE_SHEET_ID=sheet",
                        "GOOGLE_SERVICE_ACCOUNT_JSON=/tmp/service.json",
                    ]
                ),
                encoding="utf-8",
            )

            config = load_config(env_file)

        self.assertEqual(config.plaid_client_id, "client")
        self.assertEqual(config.plaid_secret, "secret")
        self.assertEqual(config.plaid_env, "production")
        self.assertEqual(config.plaid_link_products, ("auth",))
        self.assertEqual(config.plaid_request_timeout_seconds, 60)
        self.assertEqual(config.plaid_max_retries, 2)

    def test_load_config_reads_plaid_timeout_and_retries(self) -> None:
        with TemporaryDirectory() as tmpdir, patch.dict("os.environ", {}, clear=True):
            env_file = Path(tmpdir) / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "PLAID_REQUEST_TIMEOUT_SECONDS=45.5",
                        "PLAID_MAX_RETRIES=3",
                    ]
                ),
                encoding="utf-8",
            )
            config = load_config(env_file)

        self.assertEqual(config.plaid_request_timeout_seconds, 45.5)
        self.assertEqual(config.plaid_max_retries, 3)

    def test_invalid_plaid_timeout_fails(self) -> None:
        with TemporaryDirectory() as tmpdir, patch.dict("os.environ", {}, clear=True):
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("PLAID_REQUEST_TIMEOUT_SECONDS=0\n", encoding="utf-8")

            with self.assertRaisesRegex(ConfigError, "PLAID_REQUEST_TIMEOUT_SECONDS"):
                load_config(env_file)

    def test_required_plaid_config_fails_without_secret(self) -> None:
        with TemporaryDirectory() as tmpdir, patch.dict("os.environ", {}, clear=True):
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("PLAID_CLIENT_ID=client\n", encoding="utf-8")
            config = load_config(env_file)

        with self.assertRaisesRegex(ConfigError, "PLAID_SECRET"):
            require_plaid(config)

    def test_env_example_contains_no_known_secret_values(self) -> None:
        env_example = Path(".env.example").read_text(encoding="utf-8")

        self.assertIn("your-plaid-client-id", env_example)
        self.assertIn("your-plaid-secret", env_example)
        self.assertIsNone(re.search(r"PLAID_SECRET=[0-9a-f]{20,}", env_example))
        self.assertIsNone(re.search(r"PLAID_CLIENT_ID=[0-9a-f]{20,}", env_example))
