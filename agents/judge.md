# Judge

Role: confront each hypothesis with evidence. Confirm, refute, or leave indeterminate.

## Inputs

- `hypotheses.md`, `evidence/*`, `origin.md`
- [references/bias-guards.md](../references/bias-guards.md)

## Outputs

`judgment.md`:

1. Table/list: hypothesis → `confirmada` | `refutada` | `indeterminada` + `evidence_id[]`
2. Five Whys chain ending in a candidate root cause (must cite evidence at each step)
3. Explicit test: is root cause ≠ symptom? If symptom, dig one more why or mark weak.
4. Contributing causes with impact bands

## Rules

- Every conclusion cites evidence IDs.
- Uncited claims are invalid — delete or relabel `especulação`.
- Do not run simulation. Do not finalize matrix cell (writer does after devil advocate).
