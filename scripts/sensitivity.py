#!/usr/bin/env python3
"""One-variable-at-a-time sensitivity on the activity proxy model."""

from __future__ import annotations

import sys
from pathlib import Path as _Path
_SCRIPTS = _Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import argparse
from pathlib import Path

from _common import ensure_dir, read_json, utc_now, write_json


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True)
    return p.parse_args()


def failure(gap: float, cpw: float) -> bool:
    return gap >= 6 or cpw < 0.2


def main() -> int:
    args = parse_args()
    out = Path(args.out).expanduser().resolve()
    ensure_dir(out)
    params = read_json(out / "model_params.json", default={}) or {}
    backtest = read_json(out / "backtest.json", default={}) or {}

    if not backtest.get("backtest_pass"):
        write_json(
            out / "sensitivity.json",
            {
                "skipped": True,
                "reason": "backtest did not pass — qualitative verdict only",
                "variables": [],
                "checked_at": utc_now(),
            },
        )
        print("sensitivity skipped (backtest fail)")
        return 0

    gap = float(params.get("inputs", {}).get("max_gap_months") or 0)
    cpw = float(params.get("inputs", {}).get("commits_per_week_point") or 0)

    variables = []

    # Variable: gap_months
    for delta, new_gap in (("−3 months", max(gap - 3, 0)), ("−6 months", max(gap - 6, 0))):
        variables.append(
            {
                "name": "max_gap_months",
                "baseline_band": [max(gap - 1, 0), gap + 1],
                "delta": delta,
                "outcome_band": ["survives" if not failure(new_gap, cpw) else "fails"] * 2,
                "notes": f"counterfactual gap={new_gap}",
            }
        )

    # Variable: commits_per_week
    for delta, new_cpw in (("×2 activity", cpw * 2), ("×5 activity", cpw * 5)):
        variables.append(
            {
                "name": "commits_per_week",
                "baseline_band": params.get("bands", {}).get("commits_per_week", [cpw, cpw]),
                "delta": delta,
                "outcome_band": ["survives" if not failure(gap, new_cpw) else "fails"] * 2,
                "notes": f"counterfactual cpw={round(new_cpw, 3)}",
            }
        )

    payload = {
        "skipped": False,
        "checked_at": utc_now(),
        "variables": variables,
    }
    write_json(out / "sensitivity.json", payload)

    sim = out / "simulation.md"
    extra = ["\n## Sensitivity (one variable at a time)\n"]
    for v in variables:
        extra.append(
            f"- `{v['name']}` {v['delta']}: outcome band {v['outcome_band'][0]} ({v['notes']})"
        )
    if sim.exists():
        sim.write_text(sim.read_text(encoding="utf-8") + "\n".join(extra) + "\n", encoding="utf-8")
    else:
        sim.write_text("# Simulation\n\n" + "\n".join(extra) + "\n", encoding="utf-8")

    print(f"Wrote sensitivity for {len(variables)} counterfactuals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
