# Trading Journal Feedback Loop

The trading journal is a backend-only record of user/operator decision feedback around
deterministic setup artifacts. It lets a user record whether they observed, ignored, reviewed, or
paper-followed a setup, then compare that user decision note with a later deterministic signal
outcome.

This module does not place broker orders, execute broker workflows, calculate account returns, provide
financial advice, create copy-trading behavior, mutate signals, or mutate outcomes.

## Purpose

Journal entries capture:

- observed setup context
- ignored setup context
- reviewed setup context
- user decision note
- optional user bias before later outcome data
- optional links to signals, analysis runs, setup context IDs, chart screenshot runs, reports,
  audit timelines, external notes, or dataset references

Journal reviews compare a journal note with later observed behavior stored in `signal_outcomes`.
The comparison is deterministic and template-based.

## Database Tables

```txt
journal_entries
journal_entry_reviews
journal_entry_attachments
```

`journal_entries.setup_context_id` is nullable and references `setup_contexts.id` when provided.

## Status Values

```txt
draft
saved
archived
```

## Decision Types

```txt
observed
ignored
reviewed
paper_followed
external_action_taken
no_action
uncertain
```

`external_action_taken` records that the user says something happened outside this backend. It does
not import broker data or trigger broker execution.

## User Bias Values

```txt
bullish
bearish
neutral
unclear
```

## Review Labels

```txt
aligned_with_observed_outcome
conflicted_with_observed_outcome
inconclusive
insufficient_outcome_data
needs_more_review
```

## Reflection Rules

The reflection helper reads:

- journal decision type
- journal user bias
- linked or latest available deterministic signal outcome

It writes a `journal_entry_reviews` row with deterministic reflection notes and lessons. It does
not call LLMs. It does not calculate broker accounting. It does not alter the source signal,
classification, analysis run, chart screenshot run, or outcome.

High-level behavior:

- Missing or insufficient outcome data returns `insufficient_outcome_data`.
- `uncertain` decision notes return `needs_more_review`.
- Neutral, unclear, sideways, no-follow-through, or non-directional comparisons return
  `inconclusive`.
- Directional user bias that matches later observed behavior returns
  `aligned_with_observed_outcome`.
- Directional user bias that conflicts with later observed behavior returns
  `conflicted_with_observed_outcome`.

## APIs

```txt
POST /journal-entries
GET /journal-entries
GET /journal-entries/{entry_id}
PATCH /journal-entries/{entry_id}
POST /journal-entries/{entry_id}/archive
POST /journal-entries/{entry_id}/attachments
POST /journal-entries/{entry_id}/review
GET /journal-entries/{entry_id}/reviews
```

Create request:

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "userId": "00000000-0000-0000-0000-000000000000",
  "signalId": "00000000-0000-0000-0000-000000000000",
  "title": "EUR/USD London session observation",
  "decisionType": "observed",
  "userBias": "bullish",
  "userNotes": "Watched due to strong context but waited for more final candles.",
  "tags": ["london", "breakout"]
}
```

Review request:

```json
{
  "outcomeId": "00000000-0000-0000-0000-000000000000"
}
```

If `outcomeId` is omitted, the service uses the latest available outcome for the entry signal when
one exists.

Attachment request:

```json
{
  "attachmentType": "chart_screenshot",
  "referenceType": "chart_screenshot_run",
  "referenceId": "00000000-0000-0000-0000-000000000000"
}
```

Known reference types are workspace-validated when possible:

```txt
analysis_run
chart_screenshot_run
outcome
setup_context
signal
user
```

Unknown reference types are stored as metadata pointers for future backend or UI consumers.

## Future UI Usage

A future UI can use this API to let operators:

- save a note while reviewing a deterministic signal or chart screenshot
- tag recurring setup observations
- attach a signal report or audit timeline reference
- revisit the note after outcome evaluation completes
- display reflection labels and lessons without presenting broker accounting or advice

The UI should preserve the same safe language: journal entry, user decision note, later observed
behavior, reflection, lesson, and outcome comparison.
