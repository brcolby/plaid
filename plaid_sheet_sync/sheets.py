from __future__ import annotations

from typing import Any

from .config import AppConfig, ConfigError


class SheetsDependencyError(RuntimeError):
    """Raised when Google API dependencies are not installed."""


class GoogleSheetsClient:
    def __init__(self, config: AppConfig):
        if not config.google_sheet_id or not config.google_service_account_json:
            raise ConfigError("GOOGLE_SHEET_ID and GOOGLE_SERVICE_ACCOUNT_JSON are required")
        self.spreadsheet_id = config.google_sheet_id
        self.service = _build_sheets_service(str(config.google_service_account_json))

    def ensure_tabs(self, headers_by_tab: dict[str, list[str]]) -> None:
        spreadsheet = (
            self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        )
        existing = {
            sheet["properties"]["title"]
            for sheet in spreadsheet.get("sheets", [])
            if "properties" in sheet
        }
        missing = [tab for tab in headers_by_tab if tab not in existing]
        if missing:
            requests = [{"addSheet": {"properties": {"title": tab}}} for tab in missing]
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"requests": requests},
            ).execute()

        for tab, headers in headers_by_tab.items():
            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=self.spreadsheet_id, range=f"{tab}!1:1")
                .execute()
            )
            if not result.get("values"):
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{tab}!A1",
                    valueInputOption="RAW",
                    body={"values": [headers]},
                ).execute()

    def append_rows(self, tab: str, rows: list[list[Any]]) -> dict[str, Any] | None:
        if not rows:
            return None
        return (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{tab}!A1",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": rows},
            )
            .execute()
        )


def _build_sheets_service(service_account_json: str) -> Any:
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise SheetsDependencyError("Install dependencies with: pip install -e '.[dev]'") from exc

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = service_account.Credentials.from_service_account_file(
        service_account_json,
        scopes=scopes,
    )
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)

