# Workspace Overview

`GET /workspaces/{workspace_id}/overview` returns one read-only daily workspace payload for the command center.

It composes stored product readiness, provider health, data freshness, daily brief, daily workflow, read models, outcomes, pending backend-safe action items, notifications, journal prompts, and quality warnings. The endpoint does not trigger scans, call LLMs, evaluate outcomes, deliver notifications, fetch provider data, or perform broker execution.

If a section is unavailable, the response includes `missingSections` and `warnings` while still returning the rest of the payload. This keeps local/dev and partially seeded workspaces usable.

Query parameters:

- `periodStart`, `periodEnd`
- `watchlistId`
- `preferenceProfileId`
- `includeReadModels`
- `includeNotifications`
- `includeJournal`
- `includeQuality`

The endpoint is workspace-read protected when auth is enforced. In `AUTH_MODE=dev`, local header-based context continues to work.
