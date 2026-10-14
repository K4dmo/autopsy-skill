# Pré-mortem

Role: generate testable failure hypotheses **without** knowing judgment outcomes.

## Inputs allowed

- `evidence/*`, `origin.md`, [references/failure-catalog.md](../references/failure-catalog.md)

## Inputs forbidden

- `judgment.md`, `simulation.md`, `verdict.md`, any prior autopsy conclusions

## Outputs

`hypotheses.md` with **10–15** hypotheses. Each must include:

- Title
- Catalog ID if applicable (O/E/X/A)
- Previsão verificável
- Como falsear
- Evidência a buscar
- Status: `aberta`

## Rules

- Prefer falsifiable claims over narrative.
- Mix origin, execution, and external modes.
- No root-cause selection. No ranking as "the" cause.
- Numbers as bands only.
