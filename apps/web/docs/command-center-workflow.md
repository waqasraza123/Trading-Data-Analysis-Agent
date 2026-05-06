# Command Center Workflow

The command center now prefers `GET /workspaces/{workspaceId}/overview` for a daily workflow hub.

Daily loop:

1. Check readiness.
2. Review provider health and data freshness.
3. Run explicit deterministic backend tasks.
4. Generate or fetch a daily brief.
5. Review priority setup context.
6. Inspect confirmation and avoid-condition queues.
7. Review observed outcomes.
8. Add journal reflection where needed.
9. Return to command center with updated stored state.

If the overview endpoint is missing or unavailable, the existing frontend composition remains the fallback. Quick-action buttons show permission and backend-unavailable states without exposing stack traces.

All new labels are routed through safe-copy helpers. The workflow remains a deterministic market-intelligence cockpit and does not perform broker execution, auto-trading, copy trading, or financial-advice output.
