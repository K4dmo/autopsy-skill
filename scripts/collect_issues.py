#!/usr/bin/env python3
"""Collect GitHub issues/PR evidence via gh (optional)."""

from __future__ import annotations

import sys
from pathlib import Path as _Path
_SCRIPTS = _Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import argparse
import json
import shutil
from pathlib import Path

from _common import (
    ensure_dir,
    evaluate_evidence_gate,
    evidence_item,
    load_or_init_state,
    run,
    save_state,
    slugify,
    utc_now,
    write_json,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", required=True, help="Path to git repo")
    p.add_argument("--out", required=True, help="Output autopsy/<slug> directory")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    target = Path(args.target).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()
    ensure_dir(out / "evidence")
    slug = slugify(out.name if out.name != "autopsy" else target.name)
    state = load_or_init_state(out, str(target), slug)

    items: list[dict] = []
    meta: dict = {"collected_at": utc_now(), "target": str(target)}

    if shutil.which("gh") is None:
        meta["skipped"] = "gh not installed"
        write_json(out / "evidence" / "issues.json", {**meta, "items": items})
        print("Skipped issues collection: gh not installed")
        return 0

    remote = run(["git", "remote", "get-url", "origin"], cwd=target)
    if remote.returncode != 0 or "github.com" not in (remote.stdout or ""):
        meta["skipped"] = "origin is not a github.com remote"
        write_json(out / "evidence" / "issues.json", {**meta, "items": items})
        print("Skipped issues collection: non-GitHub origin")
        return 0

    n = 0

    def add(label: str, claim: str, support: str, band: str = "alta") -> None:
        nonlocal n
        n += 1
        items.append(
            evidence_item(
                id_=f"ev-issues-{n:03d}",
                source="issues",
                label=label,
                claim=claim,
                support=support,
                confidence_band=band,
            )
        )

    for kind, flag in (("issue", "issue"), ("pr", "pr")):
        result = run(
            [
                "gh",
                "issue" if kind == "issue" else "pr",
                "list",
                "--state",
                "all",
                "--limit",
                "100",
                "--json",
                "number,title,state,createdAt,closedAt,updatedAt,labels",
            ],
            cwd=target,
        )
        if result.returncode != 0:
            add(
                "fato",
                f"gh {kind} list failed",
                (result.stderr or result.stdout or "")[:500],
                band="média",
            )
            continue
        try:
            rows = json.loads(result.stdout or "[]")
        except json.JSONDecodeError:
            rows = []
        open_n = sum(1 for r in rows if str(r.get("state", "")).upper() in {"OPEN", "OPENED"})
        closed_n = len(rows) - open_n
        add("fato", f"{flag} sample size (≤100): {len(rows)}", f"gh {kind} list --state all --limit 100")
        add("fato", f"{flag} open≈{open_n} closed≈{closed_n} in sample", f"gh {kind} list states")
        # stale open
        stale = 0
        for r in rows:
            if str(r.get("state", "")).upper() not in {"OPEN", "OPENED"}:
                continue
            updated = r.get("updatedAt") or r.get("createdAt")
            if updated and updated[:4].isdigit():
                # year-level staleness hint only
                try:
                    year = int(updated[:4])
                    if year <= datetime_year_minus(1):
                        stale += 1
                except ValueError:
                    pass
        if stale:
            add(
                "inferência",
                f"Open {flag}s with last update year ≤ previous calendar year: {stale}",
                "heuristic on updatedAt",
                band="média",
            )

    write_json(out / "evidence" / "issues.json", {**meta, "items": items})
    state["gates"]["evidence_sufficient"] = evaluate_evidence_gate(out)
    save_state(out, state)
    print(f"Wrote {len(items)} issues evidence items → {out / 'evidence' / 'issues.json'}")
    return 0


def datetime_year_minus(years: int) -> int:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).year - years


if __name__ == "__main__":
    raise SystemExit(main())
