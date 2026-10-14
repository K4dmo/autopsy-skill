---
name: project-autopsy
description: >-
  Autonomous project autopsy combining pre-mortem, post-mortem, and
  counterfactual simulation to explain why a software project failed and whether
  it had potential. Use when the user runs /autopsy, asks for a project
  autopsy, pre-mortem, post-mortem, root-cause of a failed repo, or
  counterfactual analysis of a dead project.
disable-model-invocation: true
---

# Project Autopsy

Princípio: descobrir > perguntar; assumir > bloquear. Intervenção humana: 1 input inicial (alvo) + 1 revisão final.

## Quick start

```text
/autopsy <caminho-ou-url>
```

1. Resolve skill root (this directory). Runtime artifacts: `autopsy/<slug>/` under the skill root.
2. Read [references/artifact-contracts.md](references/artifact-contracts.md).
3. Run the pipeline below. Resume from last completed phase via `state.json`.

## Intake (phase 0)

Mandatory: target path, local folder, or git URL.

Infer and write to `assumptions.md` + `state.json`:

- Failure definition (abandonment, no users, shutdown, pivot-as-death — from history)
- Horizon (from first commit / last activity bands)

Unanswered doubts → assumptions. Do not block.

Slug: basename of target, sanitized (`[^a-zA-Z0-9._-]` → `-`).

## Pipeline

| # | Phase | Agent | Output |
|---|-------|-------|--------|
| 1 | Coleta | [agents/collector.md](agents/collector.md) | `evidence/*.json` |
| 2 | Origem | [agents/origin-analyst.md](agents/origin-analyst.md) | `origin.md` |
| 3 | Pré-mortem | [agents/premortem.md](agents/premortem.md) | `hypotheses.md` |
| 4 | Pós-mortem | [agents/judge.md](agents/judge.md) | `judgment.md` |
| 5 | Simulação | [agents/modeler.md](agents/modeler.md) | `simulation.md`, `sensitivity.json` |
| 6 | Veredito | [agents/writer.md](agents/writer.md) + devil advocate | `verdict.md`, `assumptions.md` |

Hard rules:

- Phase 3 written **before** reading phase 4–6 outputs.
- Every claim labeled: `fato` / `inferência` / `especulação`.
- Numbers always as ranges/bands.
- Blameless: no people analysis.

### Scripts

Run from skill root. `--out` is `autopsy/<slug>`.

```bash
python scripts/collect_git.py --target <path> --out autopsy/<slug>
python scripts/collect_issues.py --target <path> --out autopsy/<slug>
python scripts/collect_code.py --target <path> --out autopsy/<slug>
python scripts/funnel_model.py --out autopsy/<slug>
python scripts/backtest.py --out autopsy/<slug>
python scripts/sensitivity.py --out autopsy/<slug>
python scripts/validate_report.py --out autopsy/<slug>
```

Skip `collect_issues.py` gracefully if `gh` unavailable or not a GitHub remote.

## Gates (graceful degradation)

| Gate | Fail → |
|------|--------|
| Evidence sufficient? | Origin only; low confidence; skip 3–5 or mark qualitative |
| Backtest reproduces failure? | Skip sensitivity; qualitative verdict |
| Devil advocate overturns root cause? | Downgrade to `causa provável` |

Evidence sufficient heuristic (also in collector): ≥15 `fato` items across ≥2 sources, OR ≥25 `fato` from git alone, AND last activity / lifespan inferable.

After phase 4, run devil advocate ([agents/devil-advocate.md](agents/devil-advocate.md)) before locking root cause. After phase 6, run `validate_report.py`.

## State & resume

- Persist `state.json` after each phase (`phase`, `phases_completed`, `gates`).
- On interrupt: read `state.json`, continue at `phase + 1`.
- Assumption correction → re-run only affected phases:

| Assumption touches | Re-run |
|--------------------|--------|
| Evidence / target scope | 1→6 |
| Origin / market | 2→6 |
| Hypotheses framing | 3→6 |
| Judgment / root cause | 4→6 |
| Model params | 5→6 |
| Wording only | 6 |

## References (load on demand)

- [references/verdict-matrix.md](references/verdict-matrix.md)
- [references/origin-checklist.md](references/origin-checklist.md)
- [references/failure-catalog.md](references/failure-catalog.md)
- [references/bias-guards.md](references/bias-guards.md)
- Templates: [assets/report-template.md](assets/report-template.md), [assets/assumptions-template.md](assets/assumptions-template.md)

## Final handoff

Present `verdict.md` + top assumptions for human review (≤10 min). Do not ask extra questions unless the target path is missing.
