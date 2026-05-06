# First-Run Onboarding

The first-run onboarding page lives at `/onboarding`. It consumes `GET /onboarding/status`, shows
the current product readiness gate, and gives one clear next step from empty setup to command
center readiness.

The existing `/setup` wizard remains available for deeper guided setup runs. `/onboarding` links to
that wizard and to the daily workflow surfaces:

- `/data/onboarding`
- `/scanner`
- `/preferences/strategy`
- `/readiness`
- `/command-center`

## Workspace Selector

The app shell now uses a workspace selector in the shared workspace switcher slot. It loads
`GET /workspaces`, stores the selected workspace id in browser local storage, and updates the
current URL with `workspaceId` so daily pages use the selected workspace through existing API
clients.

When no workspace exists, the selector links to `/onboarding`.

## Command Center Gate

`/command-center` fetches onboarding status and shows a readiness banner before the cockpit
sections. It does not block the page completely:

- Missing workspace links to onboarding.
- Missing data links to data onboarding.
- Missing watchlist or scan config links to scanner.
- Ready workspaces show command center ready.

## Demo Mode

When backend demo mode is available, onboarding shows a Create demo workspace action. Demo data is
clearly labeled as synthetic/demo context and is not silently mixed with real provider data.

## Safety Boundary

All copy stays non-advisory. The flow configures deterministic analysis readiness only. It does not
execute broker orders, connect to brokers for orders, auto-trade, send external signal delivery,
calculate account results, or provide financial advice.
