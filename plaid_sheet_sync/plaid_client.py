from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .config import AppConfig, ConfigError


class PlaidDependencyError(RuntimeError):
    """Raised when plaid-python is not installed."""


class PlaidService:
    def __init__(self, config: AppConfig):
        self.config = config
        self.client = _build_plaid_client(config)

    def create_link_token(self, products: Sequence[str] | None = None) -> str:
        imports = _plaid_imports()
        product_names = products or self.config.plaid_link_products
        request = imports["LinkTokenCreateRequest"](
            products=[imports["Products"](product) for product in product_names],
            client_name="Personal Plaid Sheet Sync",
            country_codes=[imports["CountryCode"]("US")],
            language="en",
            user=imports["LinkTokenCreateRequestUser"](client_user_id="personal-local-user"),
        )
        response = self.client.link_token_create(request)
        data = to_plain(response)
        return data["link_token"]

    def exchange_public_token(self, public_token: str) -> dict[str, Any]:
        imports = _plaid_imports()
        request = imports["ItemPublicTokenExchangeRequest"](public_token=public_token)
        response = self.client.item_public_token_exchange(request)
        return to_plain(response)

    def get_balances(self, access_token: str) -> dict[str, Any]:
        imports = _plaid_imports()
        request = imports["AccountsBalanceGetRequest"](access_token=access_token)
        return to_plain(self.client.accounts_balance_get(request))

    def get_holdings(self, access_token: str) -> dict[str, Any]:
        imports = _plaid_imports()
        request = imports["InvestmentsHoldingsGetRequest"](access_token=access_token)
        return to_plain(self.client.investments_holdings_get(request))

    def get_liabilities(self, access_token: str) -> dict[str, Any]:
        imports = _plaid_imports()
        request = imports["LiabilitiesGetRequest"](access_token=access_token)
        return to_plain(self.client.liabilities_get(request))


def to_plain(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return {key: to_plain(child) for key, child in value.items()}
    if isinstance(value, list):
        return [to_plain(child) for child in value]
    return value


def _build_plaid_client(config: AppConfig) -> Any:
    if not config.plaid_client_id or not config.plaid_secret:
        raise ConfigError("PLAID_CLIENT_ID and PLAID_SECRET are required for Plaid commands")
    try:
        import plaid
        from plaid.api import plaid_api
    except ImportError as exc:
        raise PlaidDependencyError("Install dependencies with: pip install -e '.[dev]'") from exc

    env_hosts = {
        "sandbox": plaid.Environment.Sandbox,
        "production": plaid.Environment.Production,
    }
    development = getattr(plaid.Environment, "Development", None)
    if development is not None:
        env_hosts["development"] = development
    if config.plaid_env not in env_hosts:
        supported = ", ".join(sorted(env_hosts))
        raise ConfigError(
            f"PLAID_ENV={config.plaid_env!r} is not supported by this plaid-python "
            f"version; supported values: {supported}"
        )
    configuration = plaid.Configuration(
        host=env_hosts[config.plaid_env],
        api_key={
            "clientId": config.plaid_client_id,
            "secret": config.plaid_secret,
            "plaidVersion": "2020-09-14",
        },
    )
    return plaid_api.PlaidApi(plaid.ApiClient(configuration))


def _plaid_imports() -> dict[str, Any]:
    try:
        from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
        from plaid.model.country_code import CountryCode
        from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
        from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
        from plaid.model.liabilities_get_request import LiabilitiesGetRequest
        from plaid.model.link_token_create_request import LinkTokenCreateRequest
        from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
        from plaid.model.products import Products
    except ImportError as exc:
        raise PlaidDependencyError("Install dependencies with: pip install -e '.[dev]'") from exc

    return {
        "AccountsBalanceGetRequest": AccountsBalanceGetRequest,
        "CountryCode": CountryCode,
        "InvestmentsHoldingsGetRequest": InvestmentsHoldingsGetRequest,
        "ItemPublicTokenExchangeRequest": ItemPublicTokenExchangeRequest,
        "LiabilitiesGetRequest": LiabilitiesGetRequest,
        "LinkTokenCreateRequest": LinkTokenCreateRequest,
        "LinkTokenCreateRequestUser": LinkTokenCreateRequestUser,
        "Products": Products,
    }
