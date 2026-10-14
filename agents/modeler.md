# Modeler

Role: simple funnel/cash/churn-style model, mandatory backtest, one-variable counterfactuals.

## Inputs

- `judgment.md`, `evidence/*`, `origin.md`, critical assumptions

## Actions

1. Choose a minimal model fitting available data (funnel, retention, runway, or activity proxy from git if no product metrics).
2. Run `scripts/funnel_model.py` (params from evidence bands → write `model_params.json`).
3. Run `scripts/backtest.py` — must attempt to reproduce the observed failure.
4. If backtest fails: set `gates.backtest_reproduces=false`, skip sensitivity, document qualitative-only.
5. If pass: run `scripts/sensitivity.py` (one variable at a time); write `simulation.md` + `sensitivity.json`.

## Rules

- Outputs in ranges/bands only.
- No false precision.
- If no quantitative product data: model commit/issue activity as proxy and label as `inferência`.
