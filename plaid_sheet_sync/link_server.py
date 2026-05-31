from __future__ import annotations

import json
import threading
import webbrowser
from collections.abc import Sequence
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .plaid_client import PlaidService
from .state import StateStore


class LinkServer:
    def __init__(
        self,
        *,
        plaid: PlaidService,
        state: StateStore,
        host: str = "127.0.0.1",
        port: int = 8080,
        open_browser: bool = True,
        products: Sequence[str] | None = None,
    ):
        self.plaid = plaid
        self.state = state
        self.host = host
        self.port = port
        self.open_browser = open_browser
        self.products = products
        self.done = threading.Event()

    def run(self) -> None:
        link_token = self.plaid.create_link_token(self.products)
        handler = _handler_factory(self, link_token)
        server = ThreadingHTTPServer((self.host, self.port), handler)
        url = f"http://{self.host}:{server.server_port}"
        print(f"Plaid Link server running at {url}")
        if self.open_browser:
            webbrowser.open(url)
        try:
            while not self.done.is_set():
                server.handle_request()
        finally:
            server.server_close()

    def exchange_and_store(self, public_token: str, metadata: dict[str, Any]) -> dict[str, Any]:
        response = self.plaid.exchange_public_token(public_token)
        institution = metadata.get("institution") or {}
        item_id = response["item_id"]
        self.state.upsert_item(
            item_id=item_id,
            access_token=response["access_token"],
            institution_id=institution.get("institution_id"),
            institution_name=institution.get("name"),
            metadata=metadata,
        )
        return {
            "item_id": item_id,
            "institution_name": institution.get("name"),
        }


def _handler_factory(server_context: LinkServer, link_token: str) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib method name.
            if self.path not in {"/", "/index.html"}:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = _link_page(link_token).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802 - stdlib method name.
            if self.path != "/exchange":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
                result = server_context.exchange_and_store(
                    payload["public_token"],
                    payload.get("metadata") or {},
                )
                body = json.dumps({"ok": True, **result}).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                threading.Timer(0.2, server_context.done.set).start()
            except Exception as exc:  # noqa: BLE001 - show browser-visible setup errors.
                body = json.dumps({"ok": False, "error": str(exc)}).encode("utf-8")
                self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


def _link_page(link_token: str) -> str:
    encoded_token = json.dumps(link_token)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Plaid Sheet Sync</title>
  <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 40px; }}
    button {{ font: inherit; padding: 10px 14px; }}
    pre {{ white-space: pre-wrap; }}
  </style>
</head>
<body>
  <h1>Plaid Sheet Sync</h1>
  <button id="link">Link institution</button>
  <pre id="status"></pre>
  <script>
    const statusEl = document.getElementById('status');
    const handler = Plaid.create({{
      token: {encoded_token},
      onSuccess: async (public_token, metadata) => {{
        statusEl.textContent = 'Exchanging token locally...';
        const response = await fetch('/exchange', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ public_token, metadata }})
        }});
        const data = await response.json();
        if (!response.ok || !data.ok) {{
          statusEl.textContent = 'Error: ' + (data.error || response.statusText);
          return;
        }}
        statusEl.textContent = 'Linked ' + (data.institution_name || data.item_id) + '. You can close this tab.';
      }},
      onExit: (err) => {{
        if (err) statusEl.textContent = JSON.stringify(err, null, 2);
      }}
    }});
    document.getElementById('link').addEventListener('click', () => handler.open());
  </script>
</body>
</html>
"""
