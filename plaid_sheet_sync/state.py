from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(frozen=True)
class StoredItem:
    item_id: str
    access_token: str
    institution_id: str | None
    institution_name: str | None
    created_at: str
    updated_at: str
    last_success_at: str | None
    last_error: str | None
    metadata: dict[str, Any]


class StateStore:
    def __init__(self, path: Path):
        self.path = path.expanduser()
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._init_db()
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    item_id TEXT PRIMARY KEY,
                    access_token TEXT NOT NULL,
                    institution_id TEXT,
                    institution_name TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_success_at TEXT,
                    last_error TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL,
                    name TEXT,
                    official_name TEXT,
                    type TEXT,
                    subtype TEXT,
                    mask TEXT,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(item_id) REFERENCES items(item_id)
                )
                """
            )

    def upsert_item(
        self,
        *,
        item_id: str,
        access_token: str,
        institution_id: str | None,
        institution_name: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now = utc_now()
        metadata_json = json.dumps(metadata or {}, sort_keys=True)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO items (
                    item_id, access_token, institution_id, institution_name,
                    created_at, updated_at, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET
                    access_token = excluded.access_token,
                    institution_id = excluded.institution_id,
                    institution_name = excluded.institution_name,
                    updated_at = excluded.updated_at,
                    metadata_json = excluded.metadata_json
                """,
                (
                    item_id,
                    access_token,
                    institution_id,
                    institution_name,
                    now,
                    now,
                    metadata_json,
                ),
            )

    def list_items(self) -> list[StoredItem]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT item_id, access_token, institution_id, institution_name,
                       created_at, updated_at, last_success_at, last_error, metadata_json
                FROM items
                ORDER BY institution_name COLLATE NOCASE, item_id
                """
            ).fetchall()
        return [_item_from_row(row) for row in rows]

    def upsert_accounts(self, item_id: str, accounts: list[dict[str, Any]]) -> None:
        now = utc_now()
        with self._connect() as conn:
            for account in accounts:
                conn.execute(
                    """
                    INSERT INTO accounts (
                        account_id, item_id, name, official_name, type, subtype, mask, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(account_id) DO UPDATE SET
                        item_id = excluded.item_id,
                        name = excluded.name,
                        official_name = excluded.official_name,
                        type = excluded.type,
                        subtype = excluded.subtype,
                        mask = excluded.mask,
                        updated_at = excluded.updated_at
                    """,
                    (
                        account.get("account_id"),
                        item_id,
                        account.get("name"),
                        account.get("official_name"),
                        account.get("type"),
                        account.get("subtype"),
                        account.get("mask"),
                        now,
                    ),
                )

    def list_accounts(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT account_id, item_id, name, official_name, type, subtype, mask, updated_at
                FROM accounts
                ORDER BY item_id, name COLLATE NOCASE, account_id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_item_result(self, item_id: str, *, success: bool, error: str | None = None) -> None:
        now = utc_now()
        with self._connect() as conn:
            if success:
                conn.execute(
                    """
                    UPDATE items
                    SET last_success_at = ?, last_error = NULL, updated_at = ?
                    WHERE item_id = ?
                    """,
                    (now, now, item_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE items
                    SET last_error = ?, updated_at = ?
                    WHERE item_id = ?
                    """,
                    (error, now, item_id),
                )


def _item_from_row(row: sqlite3.Row) -> StoredItem:
    metadata_json = row["metadata_json"] or "{}"
    try:
        metadata = json.loads(metadata_json)
    except json.JSONDecodeError:
        metadata = {}
    return StoredItem(
        item_id=row["item_id"],
        access_token=row["access_token"],
        institution_id=row["institution_id"],
        institution_name=row["institution_name"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        last_success_at=row["last_success_at"],
        last_error=row["last_error"],
        metadata=metadata,
    )

