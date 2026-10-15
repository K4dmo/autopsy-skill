# Artifact Contracts

All runtime artifacts live under `autopsy/<slug>/`. Labels for claims: `fato` | `inferência` | `especulação`. Numbers always as ranges (bands), never point estimates.

## state.json

```json
{
  "slug": "string",
  "target": "path-or-url",
  "phase": 0,
  "phases_completed": [],
  "gates": {
    "evidence_sufficient": null,
    "backtest_reproduces": null,
    "devil_advocate_holds": null
  },
  "failure_definition": "string|null",
  "horizon": "string|null",
  "updated_at": "ISO-8601"
}
```

`phase`: last completed phase (0 = intake only). Resume from `phase + 1`.

## evidence/*.json

One file per source family preferred: `git.json`, `issues.json`, `code.json`. Items:

```json
{
  "id": "ev-git-001",
  "source": "git|issues|code|doc|external",
  "label": "fato|inferência|especulação",
  "claim": "short claim",
  "support": "path, sha, URL, or quote",
  "confidence_band": "baixa|média|alta",
  "observed_at": "ISO-8601|null"
}
```

## origin.md

Sections: potencial intrínseco, checklist (scores as ranges), evidências citadas (`ev-…`), gaps.

## hypotheses.md

10–15 items. Each hypothesis:

```markdown
### H01 — <title>
- Previsão verificável:
- Como falsear:
- Evidência a buscar:
- Status: aberta
```

Written **before** reading `judgment.md` / `verdict.md`.

## judgment.md

For each hypothesis: `confirmada` | `refutada` | `indeterminada` + `evidence_id[]`. Include 5 Porquês anchored in evidence. Flag if root cause looks like a symptom.

## simulation.md / sensitivity.json

`simulation.md`: model type, backtest result, counterfactuals (one variable at a time), bands.

```json
{
  "backtest_pass": false,
  "variables": [
    {
      "name": "string",
      "baseline_band": ["low", "high"],
      "delta": "string",
      "outcome_band": ["low", "high"],
      "notes": "string"
    }
  ]
}
```

## assumptions.md

Top 3–5 critical assumptions. Each: statement, impact if wrong, phases to re-run.

## verdict.md

Classification from verdict-matrix, root cause, contributing causes by impact, point of no return, confidence per conclusion, evidence citations. If a gate failed, state degraded mode explicitly.

## report.html / Desktop HTML

After phase 6 validation, `scripts/export_html.py` produces:

- `autopsy/<slug>/report.html` — self-contained interactive report (nav, filters, collapsible sections)
- Desktop copy: `autopsy-<slug>-YYYYMMDD-HHMM.html` under the user's Desktop / Área de Trabalho
- `report_export.json` — paths + `generated_at`

Content includes all phase markdown artifacts, evidence cards (filterable by label), gates, and sensitivity chart when present.
