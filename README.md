# Plaid Balance + Holdings Sync

Local-only Python tooling for polling personal Plaid Production/Trial account balances and investment holdings, then appending snapshots to Google Sheets.

## Security Notes

- Never commit `.env`, Plaid secrets, Plaid access tokens, Google service-account JSON, SQLite state, logs, or token exports.
- Runtime state defaults to `~/.plaid-balance-sync/state.sqlite`, outside this repo.
- The Plaid production secret should be rotated in the Plaid dashboard before long-term use because it was shared in chat.
- Before committing, run:

```sh
git status --short
git diff --cached
git diff
```

Confirm no secret values, access tokens, or service-account JSON are present.

## Setup

1. Create a virtual environment and install the project:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```

2. Copy `.env.example` to `.env` and fill in local values:

```sh
cp .env.example .env
```

Required values:

- `PLAID_CLIENT_ID`
- `PLAID_SECRET`
- `PLAID_ENV=production`
- `PLAID_LINK_PRODUCTS=auth`
- `GOOGLE_SERVICE_ACCOUNT_JSON=/absolute/path/to/google-service-account.json`
- `GOOGLE_SHEET_ID`

3. In Google Sheets, share the target spreadsheet with the service account email from the JSON key.

## Link Institutions

Run the local Plaid Link flow:

```sh
plaid-sheet-sync link
```

Use a product set that matches the institution type:

```sh
# Depository accounts such as Wells Fargo and Ally Savings.
plaid-sheet-sync link --products auth

# Investment and retirement accounts such as Schwab, Vanguard, and Fidelity 401k.
plaid-sheet-sync link --products investments
```

If your Plaid Trial configuration allows Balance as a Link product directly, you can also use `--products balance`. The sync command uses `/accounts/balance/get` for every linked Item and `/investments/holdings/get` where holdings are available.

If your browser does not open automatically, visit the printed `http://127.0.0.1:8080` URL. Repeat for Schwab, Vanguard, Wells Fargo, Ally Savings, and Fidelity 401k as available in your Plaid Trial/Production dashboard.

List linked Items without printing tokens:

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

The tool ensures these tabs exist and writes headers when a tab is empty:

- `current_balances`
- `balance_snapshots`
- `holding_snapshots`
- `sync_runs`

`balance_snapshots`, `holding_snapshots`, and `sync_runs` are append-only history tabs. `current_balances` is a static current-state frame: every sync clears the tab and rewrites the latest balance rows so formulas can reference stable cells.

## Scheduling

Recommended setup is macOS `launchd`, using the tracked template in `launchd/com.bcolby.plaid-sheet-sync.plist`. It runs `plaid-sheet-sync sync` every day at 6:15 AM local time and writes logs under `~/.plaid-balance-sync/`.

Before enabling the scheduled job, run one dry run and one real write:

```sh
cd /Users/bcolby/projects/plaid
. .venv/bin/activate
plaid-sheet-sync sync --dry-run
plaid-sheet-sync sync
```

Install the LaunchAgent:

```sh
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/.plaid-balance-sync"
chmod 700 "$HOME/.plaid-balance-sync"
cp /Users/bcolby/projects/plaid/launchd/com.bcolby.plaid-sheet-sync.plist "$HOME/Library/LaunchAgents/"
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.bcolby.plaid-sheet-sync.plist"
```

Run it once immediately:

```sh
launchctl kickstart -k "gui/$(id -u)/com.bcolby.plaid-sheet-sync"
```

Check logs:

```sh
tail -f "$HOME/.plaid-balance-sync/sync.log"
tail -f "$HOME/.plaid-balance-sync/sync.err.log"
```

Check launchd status:

```sh
launchctl print "gui/$(id -u)/com.bcolby.plaid-sheet-sync"
```

Unload the scheduled job:

```sh
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.bcolby.plaid-sheet-sync.plist"
```

If the plist changes after it has been loaded, reload it:

```sh
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.bcolby.plaid-sheet-sync.plist"
cp /Users/bcolby/projects/plaid/launchd/com.bcolby.plaid-sheet-sync.plist "$HOME/Library/LaunchAgents/"
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.bcolby.plaid-sheet-sync.plist"
```

Cron also works, but `launchd` is preferred on macOS. Daily cron example:

```cron
15 6 * * * cd /Users/bcolby/projects/plaid && /Users/bcolby/projects/plaid/.venv/bin/plaid-sheet-sync sync >> "$HOME/.plaid-balance-sync/sync.log" 2>&1
```

Hourly cron example:

```cron
0 * * * * cd /Users/bcolby/projects/plaid && /Users/bcolby/projects/plaid/.venv/bin/plaid-sheet-sync sync >> "$HOME/.plaid-balance-sync/sync.log" 2>&1
```

## Development

Run tests:

```sh
python -m unittest discover -s tests
```
