#!/usr/bin/env python3
"""Validate autopsy artifacts before human review."""

from __future__ import annotations

import sys
from pathlib import Path as _Path
_SCRIPTS = _Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import argparse
import re
import sys
from pathlib import Path

from _common import read_json


REQUIRED_PHASE_FILES = {
    1: ["evidence"],
    2: ["origin.md"],
    3: ["hypotheses.md"],
    4: ["judgment.md"],
    6: ["verdict.md", "assumptions.md"],
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, help="autopsy/<slug>")
    p.add_argument("--strict", action="store_true", help="Require full pipeline artifacts")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out = Path(args.out).expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []

    if not out.exists():
        print(f"ERROR: missing output dir {out}")
        return 2

    state = read_json(out / "state.json", default={}) or {}
    phase = int(state.get("phase") or 0)

    # Evidence structure
    ev = out / "evidence"
    if not ev.exists():
        errors.append("missing evidence/")
    else:
        jsons = list(ev.glob("*.json"))
        if not jsons:
            errors.append("evidence/ has no JSON files")
        for path in jsons:
            data = read_json(path, default={})
            items = data if isinstance(data, list) else data.get("items", [])
            for i, item in enumerate(items):
                for key in ("id", "source", "label", "claim", "support"):
                    if key not in item:
                        errors.append(f"{path.name}[{i}] missing {key}")
                if item.get("label") not in {"fato", "inferência", "especulação", None}:
                    if item.get("label") not in {"fato", "inferência", "especulação"}:
                        errors.append(f"{path.name}[{i}] invalid label {item.get('label')}")

    if args.strict or phase >= 6:
        for name in ("verdict.md", "assumptions.md"):
            if not (out / name).exists():
                errors.append(f"missing {name}")

    verdict = out / "verdict.md"
    if verdict.exists():
        text = verdict.read_text(encoding="utf-8")
        if "ev-" not in text and "evidence" not in text.lower():
            warnings.append("verdict.md may lack evidence citations (no ev- ids found)")
        # discourage point estimates like "42.5%" without range — soft check
        if re.search(r"\b\d+\.\d+%\b", text) and "–" not in text and "-" not in text:
            warnings.append("possible point-percentage in verdict; prefer bands")

    hyp = out / "hypotheses.md"
    if hyp.exists():
        text = hyp.read_text(encoding="utf-8")
        count = len(re.findall(r"^###\s+H\d+", text, flags=re.M))
        if count and (count < 10 or count > 15):
            warnings.append(f"hypotheses.md has {count} H## sections; expected 10–15")

    gates = state.get("gates") or {}
    if gates.get("evidence_sufficient") is False:
        warnings.append("gate evidence_sufficient=false — expect degraded verdict")
    if gates.get("backtest_reproduces") is False:
        warnings.append("gate backtest_reproduces=false — qualitative simulation only")
    if gates.get("devil_advocate_holds") is False:
        warnings.append("gate devil_advocate_holds=false — use causa provável")

    for w in warnings:
        print(f"WARN: {w}")
    for e in errors:
        print(f"ERROR: {e}")

    if errors:
        print("INVALID")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
