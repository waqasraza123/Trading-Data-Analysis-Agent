# Demo Mode Page

The web app exposes `/demo` as a local/staging product smoke page.

The page reads:

- `GET /demo-mode/status`

The run button calls:

- `POST /demo-mode/run-full-flow`

After a successful run, the page shows generated artifact counts, step status, and links into:

- command center
- daily brief
- triage
- scanner
- signal detail
- journal entry

Safety language is visible on the page. Demo mode is synthetic-only and does not use production
market data, external providers, broker connections, auto-trading, or financial-advice language.
