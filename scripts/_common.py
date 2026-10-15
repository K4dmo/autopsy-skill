"""Shared helpers for project-autopsy scripts."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def desktop_dir() -> Path:
    """Resolve the user's Desktop (Área de Trabalho) folder across locales."""
    home = Path.home()
    candidates = [
        home / "Desktop",
        home / "Área de Trabalho",
        home / "Escritorio",
        home / "Bureau",
    ]
    for path in candidates:
        if path.is_dir():
            return path
    # macOS often keeps Desktop even when Finder shows a localized name
    fallback = home / "Desktop"
    ensure_dir(fallback)
    return fallback


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def slugify(value: str) -> str:
    base = Path(value.rstrip("/")).name or "project"
    base = re.sub(r"[^a-zA-Z0-9._-]+", "-", base).strip("-._")
    return base or "project"


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def load_or_init_state(out: Path, target: str, slug: str) -> dict[str, Any]:
    path = out / "state.json"
    state = read_json(path, default=None)
    if state is None:
        state = {
            "slug": slug,
            "target": target,
            "phase": 0,
            "phases_completed": [],
            "gates": {
                "evidence_sufficient": None,
                "backtest_reproduces": None,
                "devil_advocate_holds": None,
            },
            "failure_definition": None,
            "horizon": None,
            "updated_at": utc_now(),
        }
    state["updated_at"] = utc_now()
    write_json(path, state)
    return state


def save_state(out: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = utc_now()
    write_json(out / "state.json", state)


def evidence_item(
    *,
    id_: str,
    source: str,
    label: str,
    claim: str,
    support: str,
    confidence_band: str = "alta",
    observed_at: str | None = None,
) -> dict[str, Any]:
    return {
        "id": id_,
        "source": source,
        "label": label,
        "claim": claim,
        "support": support,
        "confidence_band": confidence_band,
        "observed_at": observed_at,
    }


def count_facts(evidence_dir: Path) -> tuple[int, set[str]]:
    facts = 0
    sources: set[str] = set()
    if not evidence_dir.exists():
        return 0, sources
    for path in evidence_dir.glob("*.json"):
        data = read_json(path, default={})
        items = data if isinstance(data, list) else data.get("items", [])
        for item in items:
            if item.get("label") == "fato":
                facts += 1
                sources.add(str(item.get("source", "unknown")))
    return facts, sources


def evaluate_evidence_gate(out: Path) -> bool:
    facts, sources = count_facts(out / "evidence")
    if facts >= 25 and "git" in sources:
        return True
    if facts >= 15 and len(sources) >= 2:
        return True
    return False
