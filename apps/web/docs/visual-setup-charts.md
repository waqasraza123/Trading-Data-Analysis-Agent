# Visual Setup Charts

The setup detail page includes a compact SVG chart panel for market-intelligence review. It is a read-only visual context surface and does not create trading instructions, account projections, broker actions, alerts, or financial advice.

## Approach

- The chart is implemented with reusable SVG components under `apps/web/src/components/charts/`.
- No charting dependency is required.
- The chart handles final candle windows of roughly 30 to 200 candles and inserts bounded visual gaps when timestamps indicate missing expected intervals.
- Price scaling includes candle highs/lows and visible context zones so overlays stay inside the viewport.
- Empty, unavailable, and warning states render inside the setup detail page without blocking other setup context.

## Backend Inputs

The frontend composes existing read-only endpoints:

- `GET /signals/{signal_id}`
- `GET /analysis-runs/{analysis_run_id}`
- `GET /candles`
- `GET /candles/latest`
- `GET /candles/quality`
- `GET /signals/{signal_id}/setup-context`
- `GET /signals/{signal_id}/outcomes`
- `GET /signals/{signal_id}/advanced-features`
- `GET /intelligence-reports/signals/{signal_id}`

No backend endpoint was added for this phase.

## Displayed Context

- Recent final candles.
- Latest final candle marker.
- Signal window.
- Observation zones.
- Invalidation context.
- Target context zones.
- Support/resistance context when advanced features are available.
- Review marker for the signal pattern context.
- Setup quality, freshness, data quality, and final-candle count badges.
- Data quality warnings.
- Outcome markers using observed follow-through, observed reversal, no follow-through observed, or insufficient outcome data.

## Safe Terminology

The chart uses market-intelligence labels only:

- Observation zone.
- Invalidation context.
- Target context zone.
- Review marker.
- Signal window.
- Latest final candle.
- Observed follow-through.
- Observed reversal.

It must not show order, account-result, certainty, or broker-execution language.
