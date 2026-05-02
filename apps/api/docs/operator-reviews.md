# Operator Review Queue

Operator reviews are backend review records for humans or future operator workflows. The module
stores review items and review events; it does not send alerts, execute actions, change signals, or
apply calibration changes.

## Purpose

Review items can represent quality findings, action-plan concerns, calibration recommendation
review, screenshot review, readiness blockers, or other backend-safe operator follow-up.

Expected routes:

```txt
POST /operator-reviews
GET /operator-reviews
GET /operator-reviews/{review_item_id}
POST /operator-reviews/{review_item_id}/assign
POST /operator-reviews/{review_item_id}/status
POST /operator-reviews/{review_item_id}/resolve
POST /operator-reviews/{review_item_id}/dismiss
GET /operator-reviews/{review_item_id}/events
```

## Integration

Decision readiness may treat unresolved high or urgent review items as warnings or blockers.
Quality findings, action items, screenshot review state, and calibration recommendations may be
adapted into review items only through explicit APIs or service calls.

## Safety

Review records are advisory operator workflow records. They must not execute action items, mutate
signals, mark pattern candidates selected, update strategy profiles, send notifications, call
brokers, or provide financial advice.
