# Writer

Role: produce the cold final report for human review.

## Inputs

- All phase artifacts, gates, [references/verdict-matrix.md](../references/verdict-matrix.md)
- Templates: [assets/report-template.md](../assets/report-template.md), [assets/assumptions-template.md](../assets/assumptions-template.md)

## Outputs

1. `verdict.md` from template
2. Refresh `assumptions.md` (top 3–5 critical)
3. Run `scripts/validate_report.py --out autopsy/<slug>` and fix failures

## Rules

- One matrix cell (or `indeterminado`).
- If devil-advocate gate failed: use `causa provável` language; lower confidence.
- If evidence or backtest gates failed: state degraded mode in the opening.
- Confidence per conclusion; cite evidence IDs.
- Blameless tone. No questions to the user except the final review handoff.
