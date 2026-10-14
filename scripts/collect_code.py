#!/usr/bin/env python3
"""Collect lightweight code/structure evidence."""

from __future__ import annotations

import sys
from pathlib import Path as _Path
_SCRIPTS = _Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import argparse
import re
from pathlib import Path

from _common import (
    ensure_dir,
    evaluate_evidence_gate,
    evidence_item,
    load_or_init_state,
    save_state,
    slugify,
    utc_now,
    write_json,
)

SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
    ".next",
    "coverage",
    "autopsy",
    "vendor",
}

MARKERS = {
    "readme": re.compile(r"^readme(\.|$)", re.I),
    "license": re.compile(r"^license(\.|$)", re.I),
    "dockerfile": re.compile(r"^dockerfile", re.I),
    "ci": re.compile(r"^\.github$|^\.gitlab-ci\.yml$|^\.circleci$", re.I),
}

MANIFESTS = {
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "Gemfile",
    "composer.json",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", required=True)
    p.add_argument("--out", required=True)
    return p.parse_args()


def iter_files(root: Path, limit: int = 8000):
    count = 0
    for path in root.rglob("*"):
        if count >= limit:
            break
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        count += 1
        yield path


def main() -> int:
    args = parse_args()
    target = Path(args.target).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()
    ensure_dir(out / "evidence")
    slug = slugify(out.name if out.name != "autopsy" else target.name)
    state = load_or_init_state(out, str(target), slug)

    items: list[dict] = []
    n = 0

    def add(label: str, claim: str, support: str, band: str = "alta") -> None:
        nonlocal n
        n += 1
        items.append(
            evidence_item(
                id_=f"ev-code-{n:03d}",
                source="code",
                label=label,
                claim=claim,
                support=support,
                confidence_band=band,
            )
        )

    files = list(iter_files(target))
    add("fato", f"Indexed files (cap): {len(files)}", "rglob with skip dirs")

    exts: dict[str, int] = {}
    todo_hits = 0
    test_files = 0
    for path in files:
        ext = path.suffix.lower() or "<none>"
        exts[ext] = exts.get(ext, 0) + 1
        name = path.name
        if re.search(r"test|spec", name, re.I) or "/tests/" in str(path).replace("\\", "/").lower():
            test_files += 1
        if path.stat().st_size <= 200_000 and ext in {
            ".py",
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            ".go",
            ".rs",
            ".java",
            ".md",
        }:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            todo_hits += len(re.findall(r"\bTODO\b|\bFIXME\b", text))

    top_exts = sorted(exts.items(), key=lambda x: -x[1])[:8]
    if top_exts:
        add(
            "fato",
            "Top extensions: " + ", ".join(f"{e}={c}" for e, c in top_exts),
            "file extension histogram",
        )

    for manifest in MANIFESTS:
        if (target / manifest).exists():
            add("fato", f"Manifest present: {manifest}", str(target / manifest))

    readme = next((p for p in target.iterdir() if p.is_file() and MARKERS["readme"].match(p.name)), None)
    if readme:
        add("fato", f"README present: {readme.name}", str(readme))
        try:
            text = readme.read_text(encoding="utf-8", errors="ignore")
            add("fato", f"README length ~{len(text)} chars", str(readme))
        except OSError:
            pass
    else:
        add("fato", "No README at repo root", str(target))

    if (target / ".github").is_dir() or (target / ".gitlab-ci.yml").exists():
        add("fato", "CI config directory/file detected", ".github or .gitlab-ci.yml")
    else:
        add("fato", "No common CI config detected at root", "missing .github / .gitlab-ci.yml")

    add("fato", f"Test-like file count (name/path heuristic): {test_files}", "test|spec|/tests/")
    add("fato", f"TODO/FIXME hit count (sampled text files): {todo_hits}", "regex over sampled sources")

    if test_files == 0:
        add(
            "inferência",
            "Little/no automated test footprint visible from filenames",
            "test_files==0",
            band="média",
        )

    write_json(
        out / "evidence" / "code.json",
        {"collected_at": utc_now(), "target": str(target), "items": items},
    )

    # refresh summary
    summary = out / "evidence" / "summary.md"
    existing = summary.read_text(encoding="utf-8") if summary.exists() else "# Evidence summary\n\n"
    if "code items:" not in existing:
        existing += f"- code items: {len(items)}\n"
        summary.write_text(existing, encoding="utf-8")

    state["gates"]["evidence_sufficient"] = evaluate_evidence_gate(out)
    completed = set(state.get("phases_completed") or [])
    completed.add(1)
    state["phases_completed"] = sorted(completed)
    state["phase"] = max(state.get("phase", 0), 1)
    save_state(out, state)
    print(f"Wrote {len(items)} code evidence items → {out / 'evidence' / 'code.json'}")
    print(f"evidence_sufficient={state['gates']['evidence_sufficient']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
