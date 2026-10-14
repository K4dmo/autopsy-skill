#!/usr/bin/env python3
"""Collect git history evidence for a project autopsy."""

from __future__ import annotations

import sys
from pathlib import Path as _Path
_SCRIPTS = _Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import argparse
import statistics
from collections import Counter
from datetime import datetime
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


def git(repo: Path, *args: str) -> str:
    result = run(["git", *args], cwd=repo)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def parse_dates(raw: str) -> list[datetime]:
    dates: list[datetime] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            dates.append(datetime.fromisoformat(line.replace("Z", "+00:00")))
        except ValueError:
            continue
    return dates


def month_key(dt: datetime) -> str:
    return f"{dt.year:04d}-{dt.month:02d}"


def main() -> int:
    args = parse_args()
    target = Path(args.target).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()
    ensure_dir(out / "evidence")

    if not (target / ".git").exists() and not (target / ".git").is_file():
        # allow worktrees / .git file
        probe = run(["git", "rev-parse", "--is-inside-work-tree"], cwd=target)
        if probe.returncode != 0:
            write_json(
                out / "evidence" / "git.json",
                {
                    "collected_at": utc_now(),
                    "error": f"Not a git repository: {target}",
                    "items": [],
                },
            )
            return 1

    slug = slugify(out.name if out.name != "autopsy" else target.name)
    state = load_or_init_state(out, str(target), slug)

    items: list[dict] = []
    n = 0

    def add(label: str, claim: str, support: str, band: str = "alta", when: str | None = None) -> None:
        nonlocal n
        n += 1
        items.append(
            evidence_item(
                id_=f"ev-git-{n:03d}",
                source="git",
                label=label,
                claim=claim,
                support=support,
                confidence_band=band,
                observed_at=when,
            )
        )

    head = git(target, "rev-parse", "HEAD")
    if head:
        add("fato", f"HEAD is {head[:12]}", f"git rev-parse HEAD → {head}")

    branch = git(target, "rev-parse", "--abbrev-ref", "HEAD")
    if branch:
        add("fato", f"Current branch is {branch}", "git rev-parse --abbrev-ref HEAD")

    remote = git(target, "remote", "get-url", "origin")
    if remote:
        add("fato", f"Origin remote is {remote}", "git remote get-url origin")

    commit_count = git(target, "rev-list", "--count", "HEAD")
    if commit_count.isdigit():
        add("fato", f"Total commits on HEAD: {commit_count}", "git rev-list --count HEAD")

    authors_raw = git(target, "shortlog", "-sn", "HEAD")
    authors = [ln for ln in authors_raw.splitlines() if ln.strip()]
    if authors:
        add("fato", f"Distinct author lines in shortlog: {len(authors)}", "git shortlog -sn HEAD")
        top = authors[0].strip()
        add("fato", f"Top author line: {top}", "git shortlog -sn HEAD")

    date_raw = git(target, "log", "--format=%cI", "HEAD")
    dates = parse_dates(date_raw)
    if dates:
        first, last = min(dates), max(dates)
        add(
            "fato",
            f"First commit (author/committer iso range min): {first.date().isoformat()}",
            "git log --format=%cI",
            when=first.isoformat(),
        )
        add(
            "fato",
            f"Last commit: {last.date().isoformat()}",
            "git log --format=%cI",
            when=last.isoformat(),
        )
        span_days = max((last - first).days, 0)
        add(
            "inferência",
            f"Active lifespan band: ~{span_days} days between first and last commit",
            f"delta({last.date()}, {first.date()})",
            band="média",
        )
        state["horizon"] = f"{first.date().isoformat()} → {last.date().isoformat()} (~{span_days}d)"

        by_month = Counter(month_key(d) for d in dates)
        if by_month:
            peak_m, peak_n = by_month.most_common(1)[0]
            add("fato", f"Peak commit month {peak_m} with {peak_n} commits", "monthly histogram of %cI")
            months_sorted = sorted(by_month)
            # gap detection: missing months between first and last
            zero_streak = 0
            max_zero = 0
            # iterate calendar months roughly via sorted keys density
            counts = [by_month[m] for m in months_sorted]
            if len(counts) >= 2:
                add(
                    "inferência",
                    f"Monthly commit counts range: {min(counts)}–{max(counts)} (median {statistics.median(counts):.0f})",
                    "distribution of commits/month",
                    band="média",
                )
            # consecutive dry months in sorted month keys (string order works for YYYY-MM)
            prev = None
            for m in months_sorted:
                if prev:
                    # count gap size in months between prev and m
                    py, pm = map(int, prev.split("-"))
                    cy, cm = map(int, m.split("-"))
                    gap = (cy - py) * 12 + (cm - pm) - 1
                    if gap > max_zero:
                        max_zero = gap
                prev = m
                if by_month[m] == 0:
                    zero_streak += 1
                    max_zero = max(max_zero, zero_streak)
                else:
                    zero_streak = 0
            if max_zero >= 2:
                add(
                    "fato",
                    f"Largest gap between active months: ~{max_zero} month(s) without commits",
                    "gaps in YYYY-MM commit histogram",
                )
                if max_zero >= 6 and not state.get("failure_definition"):
                    state["failure_definition"] = (
                        f"Inferred abandonment risk: ≥{max_zero} months without commits after activity"
                    )

    tags = git(target, "tag", "--list")
    tag_list = [t for t in tags.splitlines() if t.strip()]
    add("fato", f"Tag count: {len(tag_list)}", "git tag --list")
    if tag_list[:5]:
        add("fato", f"Sample tags: {', '.join(tag_list[:5])}", "git tag --list")

    # churn proxy: files changed in last 50 commits
    numstat = git(target, "log", "-n", "50", "--pretty=tformat:", "--numstat")
    added = deleted = files = 0
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit():
            added += int(parts[0])
            deleted += int(parts[1])
            files += 1
    if files:
        add(
            "fato",
            f"In last ≤50 commits: +{added}/-{deleted} lines across {files} file deltas",
            "git log -n 50 --numstat",
        )

    default_branch = git(target, "symbolic-ref", "refs/remotes/origin/HEAD")
    if default_branch:
        add("fato", f"Origin HEAD ref: {default_branch}", "git symbolic-ref refs/remotes/origin/HEAD")

    payload = {
        "collected_at": utc_now(),
        "target": str(target),
        "items": items,
    }
    write_json(out / "evidence" / "git.json", payload)

    summary_path = out / "evidence" / "summary.md"
    facts = sum(1 for i in items if i["label"] == "fato")
    inf = sum(1 for i in items if i["label"] == "inferência")
    summary_path.write_text(
        f"# Evidence summary\n\n"
        f"- git items: {len(items)} (fato={facts}, inferência={inf})\n"
        f"- collected_at: {utc_now()}\n",
        encoding="utf-8",
    )

    state["gates"]["evidence_sufficient"] = evaluate_evidence_gate(out)
    if 1 not in state.get("phases_completed", []):
        # collection may be partial until issues/code also run; still mark progress lightly
        pass
    save_state(out, state)
    print(f"Wrote {len(items)} git evidence items → {out / 'evidence' / 'git.json'}")
    print(f"evidence_sufficient={state['gates']['evidence_sufficient']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
