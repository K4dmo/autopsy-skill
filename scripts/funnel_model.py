#!/usr/bin/env python3
"""Build a minimal activity/funnel proxy model from evidence bands."""

from __future__ import annotations

import sys
from pathlib import Path as _Path
_SCRIPTS = _Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import argparse
import re
from pathlib import Path

from _common import ensure_dir, read_json, save_state, load_or_init_state, utc_now, write_json


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, help="autopsy/<slug> directory")
    return p.parse_args()


def load_items(out: Path) -> list[dict]:
    items: list[dict] = []
    ev = out / "evidence"
    if not ev.exists():
        return items
    for path in ev.glob("*.json"):
        data = read_json(path, default={})
        chunk = data if isinstance(data, list) else data.get("items", [])
        items.extend(chunk)
    return items


def extract_commit_count(items: list[dict]) -> int | None:
    for item in items:
        m = re.search(r"Total commits on HEAD: (\d+)", item.get("claim", ""))
        if m:
            return int(m.group(1))
    return None


def extract_span_days(items: list[dict]) -> int | None:
    for item in items:
        m = re.search(r"~(\d+) days", item.get("claim", ""))
        if m:
            return int(m.group(1))
    return None


def extract_gap_months(items: list[dict]) -> int | None:
    for item in items:
        m = re.search(r"~(\d+) month", item.get("claim", ""))
        if m and "gap" in item.get("claim", "").lower():
            return int(m.group(1))
    return None


def main() -> int:
    args = parse_args()
    out = Path(args.out).expanduser().resolve()
    ensure_dir(out)
    items = load_items(out)
    commits = extract_commit_count(items) or 0
    span = extract_span_days(items) or 0
    gap = extract_gap_months(items) or 0

    # Proxy funnel: awareness→activation→retention as commit intensity bands
    weekly = (commits / max(span / 7, 1)) if span else 0
    params = {
        "model": "git_activity_proxy",
        "created_at": utc_now(),
        "inputs": {
            "commits": commits,
            "span_days": span,
            "max_gap_months": gap,
            "commits_per_week_point": round(weekly, 3),
        },
        "bands": {
            "commits_per_week": [
                round(max(weekly * 0.7, 0), 3),
                round(weekly * 1.3 + 0.01, 3),
            ],
            "abandonment_gap_months": [max(gap - 1, 0), gap + 1],
        },
        "failure_proxy": {
            "rule": "gap_months >= 6 OR commits_per_week < 0.2 after peak",
            "observed_gap_months": gap,
            "observed_cpw": round(weekly, 3),
        },
        "notes": "Product metrics absent → git activity used as labeled inferência proxy.",
    }
    write_json(out / "model_params.json", params)

    state_path = out / "state.json"
    if state_path.exists():
        save_state(out, read_json(state_path) or {})
    else:
        load_or_init_state(out, str(out), out.name)

    print(f"Wrote model_params.json (cpw≈{weekly:.3f}, gap_months={gap})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
