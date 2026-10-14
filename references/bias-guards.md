# Bias Guards

## Retrospective bias

- Write `hypotheses.md` **before** reading judgment/verdict.
- Pré-mortem agent must not see phase 4–6 artifacts.
- Prefer falsifiable predictions over story fit.

## Plausible but false narrative

- Devil advocate must propose ≥3 alternate root causes.
- Every root-cause claim needs ≥2 independent evidence IDs when possible.
- If only one thin evidence thread: mark `causa provável` or `indeterminado`.

## False numeric rigor

- No single-point forecasts.
- Always bands: `baixa|média|alta` or numeric ranges.
- Simulation without passing backtest → qualitative verdict only.

## Insufficient data

- Gate `evidence_sufficient`: if fail → origin autopsy only, low confidence.
- Missing private data → assumption in `assumptions.md`, do not invent.

## Propagation of bad assumptions

- Critical assumptions (top 3–5) highlighted in `assumptions.md`.
- On correction: re-run only affected phases (see SKILL.md dependency map).

## Context overflow

- Keep phase outputs on disk; pass summaries + paths into next phase, not raw dumps.
- Collector never opines; opinions belong in origin/judge/writer only.
