#!/usr/bin/env python3
"""Backtest whether the proxy model reproduces observed failure."""

from __future__ import annotations

import sys
from pathlib import Path as _Path
_SCRIPTS = _Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import argparse
from pathlib import Path

from _common import ensure_dir, read_json, save_state, utc_now, write_json


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out = Path(args.out).expanduser().resolve()
    ensure_dir(out)
    params = read_json(out / "model_params.json", default=None)
    state = read_json(out / "state.json", default={}) or {}

    if not params:
        result = {
            "backtest_pass": False,
            "reason": "missing model_params.json — run funnel_model.py first",
            "checked_at": utc_now(),
        }
        write_json(out / "backtest.json", result)
        gates = state.setdefault("gates", {})
        gates["backtest_reproduces"] = False
        save_state(out, state)
        print("backtest_pass=false (no model)")
        return 1

    gap = int(params.get("inputs", {}).get("max_gap_months") or 0)
    cpw = float(params.get("inputs", {}).get("commits_per_week_point") or 0)
    span = int(params.get("inputs", {}).get("span_days") or 0)
    # Reproduce "failure" if long inactivity gap OR sustained near-zero activity on a mature timeline
    matured = span >= 90
    passed = gap >= 6 or (matured and cpw < 0.2)
    reason = []
    if gap >= 6:
        reason.append(f"gap_months={gap} >= 6")
    if matured and cpw < 0.2:
        reason.append(f"commits_per_week={cpw} < 0.2 over span_days={span}")
    if not reason:
        reason.append("activity still healthy under proxy rules — failure not reproduced")

    result = {
        "backtest_pass": passed,
        "reason": "; ".join(reason),
        "checked_at": utc_now(),
        "model": params.get("model"),
    }
    write_json(out / "backtest.json", result)

    gates = state.setdefault("gates", {})
    gates["backtest_reproduces"] = passed
    completed = set(state.get("phases_completed") or [])
    if passed:
        completed.add(5)
    state["phases_completed"] = sorted(completed)
    save_state(out, state)

    sim = out / "simulation.md"
    status = "PASS" if passed else "FAIL"
    sim.write_text(
        f"# Simulation\n\n"
        f"## Backtest\n\n"
        f"- Result: **{status}**\n"
        f"- Reason: {result['reason']}\n"
        f"- Model: `{params.get('model')}`\n\n"
        f"Numbers are bands/proxies only.\n",
        encoding="utf-8",
    )
    print(f"backtest_pass={passed}")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
