from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_STATE_PATH = Path("~/.plaid-balance-sync/state.sqlite").expanduser()


class ConfigError(RuntimeError):
    """Raised when required local configuration is missing or invalid."""


@dataclass(frozen=True)
class AppConfig:
    plaid_client_id: str | None
    plaid_secret: str | None
    plaid_env: str
    plaid_link_products: tuple[str, ...]
    plaid_request_timeout_seconds: float
    plaid_max_retries: int
    google_service_account_json: Path | None
    google_sheet_id: str | None
    state_db: Path


def load_config(env_file: Path | str = ".env") -> AppConfig:
    values = _read_env_file(Path(env_file))

    def get(name: str, default: str | None = None) -> str | None:
        value = os.environ.get(name, values.get(name, default))
        if value is None:
            return None
        value = value.strip()
        return value or None

    state_path = Path(get("PLAID_SYNC_STATE_DB") or DEFAULT_STATE_PATH).expanduser()
    google_json = get("GOOGLE_SERVICE_ACCOUNT_JSON")

    config = AppConfig(
        plaid_client_id=get("PLAID_CLIENT_ID"),
        plaid_secret=get("PLAID_SECRET"),
        plaid_env=(get("PLAID_ENV", "production") or "production").lower(),
        plaid_link_products=_parse_csv(get("PLAID_LINK_PRODUCTS", "auth") or "auth"),
        plaid_request_timeout_seconds=_parse_positive_float(
            "PLAID_REQUEST_TIMEOUT_SECONDS",
            get("PLAID_REQUEST_TIMEOUT_SECONDS", "60") or "60",
        ),
        plaid_max_retries=_parse_non_negative_int(
            "PLAID_MAX_RETRIES",
            get("PLAID_MAX_RETRIES", "2") or "2",
        ),
        google_service_account_json=Path(google_json).expanduser() if google_json else None,
        google_sheet_id=get("GOOGLE_SHEET_ID"),
        state_db=state_path,
    )
    if config.plaid_env not in {"sandbox", "development", "production"}:
        raise ConfigError("PLAID_ENV must be one of: sandbox, development, production")
    if not config.plaid_link_products:
        raise ConfigError("PLAID_LINK_PRODUCTS must contain at least one Plaid product")
    return config


def require_plaid(config: AppConfig) -> None:
    missing = []
    if not config.plaid_client_id:
        missing.append("PLAID_CLIENT_ID")
    if not config.plaid_secret:
        missing.append("PLAID_SECRET")
    if missing:
        raise ConfigError(f"Missing Plaid config: {', '.join(missing)}")


def require_sheets(config: AppConfig) -> None:
    missing = []
    if not config.google_sheet_id:
        missing.append("GOOGLE_SHEET_ID")
    if not config.google_service_account_json:
        missing.append("GOOGLE_SERVICE_ACCOUNT_JSON")
    elif not config.google_service_account_json.exists():
        raise ConfigError(
            f"GOOGLE_SERVICE_ACCOUNT_JSON does not exist: {config.google_service_account_json}"
        )
    if missing:
        raise ConfigError(f"Missing Google Sheets config: {', '.join(missing)}")


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def _parse_csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip().lower() for part in value.split(",") if part.strip())


def _parse_positive_float(name: str, value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a positive number") from exc
    if parsed <= 0:
        raise ConfigError(f"{name} must be a positive number")
    return parsed


def _parse_non_negative_int(name: str, value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a non-negative integer") from exc
    if parsed < 0:
        raise ConfigError(f"{name} must be a non-negative integer")
    return parsed
