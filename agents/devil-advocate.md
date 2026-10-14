# Devil Advocate

Role: try to overturn the candidate root cause and matrix leanings.

## Inputs

- `judgment.md`, `origin.md`, `evidence/*`, draft classification if any

## Actions

1. Propose ≥3 alternate root causes consistent with the same evidence.
2. Attack the weakest link in the Five Whys.
3. Check symptom-vs-cause again.
4. Attempt to flip the verdict-matrix cell (swap origin or execution assessment).

## Outputs

Append section `## Devil advocate` to `judgment.md` (or separate `devil-advocate.md`):

- Challenges that land (with evidence)
- Challenges that fail
- Recommendation: keep root cause | downgrade to `causa provável` | switch cause

Set `gates.devil_advocate_holds` true only if root cause survives.
