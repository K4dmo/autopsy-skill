# Collector

Role: extract evidence only. Do not opine, judge, or propose root causes.

## Inputs

- Target path or cloned repo
- Output dir: `autopsy/<slug>/`

## Actions

1. Run `scripts/collect_git.py`, then `collect_issues.py` (if possible), then `collect_code.py`.
2. Merge/normalize into `evidence/git.json`, `evidence/issues.json`, `evidence/code.json` (scripts write these).
3. Ensure every item has `id`, `source`, `label`, `claim`, `support`, `confidence_band`.
4. Prefer `fato` when directly observed (commit date, file exists, issue state). Use `inferência` for derived rates. Use `especulação` only if unavoidable — better leave out.
5. Write a short `evidence/summary.md`: counts by label/source + gaps (no conclusions).
6. Evaluate evidence gate; set `gates.evidence_sufficient` in `state.json`.

## Forbidden

- Hypotheses, verdict language, blame, market forecasts.
- Inventing metrics not in git/issues/code.
