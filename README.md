# Plaid Sheet Sync

Local Python tooling for linking Plaid institutions, polling account data, and writing snapshots to Google Sheets.

By default the sync writes balances and investment holdings only. Liabilities are optional and must be enabled explicitly so existing spreadsheets keep their current shape.

## What It Syncs

- Account balances from Plaid Accounts Balance
- Investment holdings from Plaid Investments, when the linked Item has investment accounts
- Debt/liability snapshots from Plaid Liabilities, only when `--include-liabilities` is used

The tool never initiates payments or payoff flows.

## Security Notes

- Never commit `.env`, Plaid secrets, Plaid access tokens, Google service-account JSON, SQLite state, logs, or token exports.
- Runtime state defaults to `~/.plaid-balance-sync/state.sqlite`, outside this repo.
- Share the destination spreadsheet only with the Google service-account email that needs write access.
- Before committing, check for secrets:

```sh
git status --short
git diff --cached
git diff
```

## Setup

Create a virtual environment and install the project:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```

Copy the example environment file and fill in local values:

```sh
cp .env.example .env
```

Required values:

- `PLAID_CLIENT_ID`
- `PLAID_SECRET`
- `PLAID_ENV`, usually `production`
- `PLAID_LINK_PRODUCTS`, usually `auth`
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `GOOGLE_SHEET_ID`

In Google Sheets, share the target spreadsheet with the service account email from the JSON key.

Optional Plaid transport settings:

- `PLAID_REQUEST_TIMEOUT_SECONDS`, default `60`, bounds each Plaid HTTP request.
- `PLAID_MAX_RETRIES`, default `2`, retries transient transport errors and retryable Plaid server responses.

These settings keep a scheduled sync from hanging indefinitely if a bank or Plaid connection stalls. Balance calls are real-time and can occasionally take 30 seconds or more, so avoid setting the timeout too low.

## Link Institutions

Run the local Plaid Link flow:

```sh
plaid-sheet-sync link
```

Use a product set that matches the institution and account type:

```sh
# Depository accounts such as checking and savings.
plaid-sheet-sync link --products auth

# Investment and retirement accounts.
plaid-sheet-sync link --products investments

# Credit cards, student loans, and mortgages.
plaid-sheet-sync link --products liabilities
```

You can also request multiple products when your Plaid environment and institution support them:

```sh
plaid-sheet-sync link --products auth,liabilities
```

If your browser does not open automatically, visit the printed local URL. Repeat the link flow for each institution you want to sync.

List linked Items without printing access tokens:

```sh
plaid-sheet-sync list
```

## Sync

Dry run without writing to Google Sheets:

```sh
plaid-sheet-sync sync --dry-run
```

Append balance and holding snapshots:

```sh
plaid-sheet-sync sync
```

The default sync ensures these tabs exist:

- `current_balances`
- `balance_snapshots`
- `holding_snapshots`
- `sync_runs`

`balance_snapshots`, `holding_snapshots`, and `sync_runs` are append-only history tabs. `current_balances` is rewritten on every sync with the latest balance rows so formulas can reference stable cells.

## Optional Liabilities

Liabilities are opt-in. A normal `plaid-sheet-sync sync` does not call Plaid Liabilities, does not create a `liability_snapshots` tab, and does not change the existing tab layout.

To sync debt data:

```sh
plaid-sheet-sync link --products liabilities
plaid-sheet-sync sync --include-liabilities
```

Liability rows are appended to `liability_snapshots` and include current debt balances, credit APR summaries, student loan or mortgage interest rates, next payment amounts and due dates, loan status, and related institution/account identifiers.

If you do not have liabilities or do not want the extra tab, do not pass `--include-liabilities`.

## Scheduling

Any scheduler that can run a shell command works. Run a dry run first, then a real write:

```sh
cd /path/to/plaid-sheet-sync
. .venv/bin/activate
plaid-sheet-sync sync --dry-run
plaid-sheet-sync sync
```

Example cron entry for a daily sync:

```cron
15 6 * * * cd /path/to/plaid-sheet-sync && /path/to/plaid-sheet-sync/.venv/bin/plaid-sheet-sync sync >> "$HOME/.plaid-balance-sync/sync.log" 2>&1
```

For macOS, the repo includes a `launchd` example that can be copied and adjusted for your local checkout path.

## Development

Run tests:

```sh
python -m unittest discover -s tests
```
