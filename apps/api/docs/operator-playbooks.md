# Operator Playbook Policy Engine

Operator playbooks evaluate persisted backend context and produce safe manual-review
recommendations. They do not execute actions, auto-apply profile changes, create alerts, or create
review items unless a future explicit workflow is added.

## APIs

```txt
GET /operator-playbooks
GET /operator-playbooks/{key}
POST /operator-playbooks/seed
POST /operator-playbooks/evaluate
GET /operator-playbooks/evaluations
```

## Recommendation Types

```txt
review_data_quality
review_profile_simulation
review_decision_readiness
review_market_session
no_action
```

## Settings

```txt
OPERATOR_PLAYBOOK_VERSION=v1
OPERATOR_PLAYBOOK_SEED_ENABLED=true
```
