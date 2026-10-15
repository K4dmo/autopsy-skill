#!/usr/bin/env python3
"""Export autopsy artifacts to a visual interactive HTML report on the Desktop."""

from __future__ import annotations

import sys
from pathlib import Path as _Path

_SCRIPTS = _Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import argparse
import html
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from _common import desktop_dir, ensure_dir, read_json, utc_now, write_json


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, help="autopsy/<slug>")
    p.add_argument(
        "--desktop",
        action="store_true",
        default=True,
        help="Also write a copy to the user's Desktop (default: on)",
    )
    p.add_argument(
        "--no-desktop",
        action="store_true",
        help="Skip Desktop copy; only write autopsy/<slug>/report.html",
    )
    return p.parse_args()


# --- Markdown (lightweight) -------------------------------------------------

def _escape(text: str) -> str:
    return html.escape(text, quote=False)


def _inline(text: str) -> str:
    text = _escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2" target="_blank" rel="noopener">\1</a>',
        text,
    )
    return text


def md_to_html(md: str) -> str:
    if not md or not md.strip():
        return '<p class="empty">—</p>'

    lines = md.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    in_code = False
    code_lang = ""
    code_buf: list[str] = []
    list_type: str | None = None

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            out.append(f"</{list_type}>")
            list_type = None

    while i < len(lines):
        line = lines[i]

        if line.startswith("```"):
            if in_code:
                body = _escape("\n".join(code_buf))
                out.append(f'<pre><code class="lang-{_escape(code_lang)}">{body}</code></pre>')
                code_buf = []
                in_code = False
                code_lang = ""
            else:
                close_list()
                in_code = True
                code_lang = line[3:].strip()
            i += 1
            continue

        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # Table block
        if "|" in line and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:-]+\|", lines[i + 1]):
            close_list()
            rows: list[str] = []
            while i < len(lines) and "|" in lines[i]:
                rows.append(lines[i])
                i += 1
            out.append(_table_html(rows))
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            close_list()
            level = len(heading.group(1))
            out.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
            i += 1
            continue

        hr = re.match(r"^(-{3,}|\*{3,}|_{3,})\s*$", line)
        if hr:
            close_list()
            out.append("<hr>")
            i += 1
            continue

        ul = re.match(r"^(\s*)[-*+]\s+(.*)$", line)
        ol = re.match(r"^(\s*)\d+\.\s+(.*)$", line)
        if ul or ol:
            kind = "ul" if ul else "ol"
            content = ul.group(2) if ul else ol.group(2)  # type: ignore[union-attr]
            if list_type != kind:
                close_list()
                list_type = kind
                out.append(f"<{kind}>")
            out.append(f"<li>{_inline(content)}</li>")
            i += 1
            continue

        if not line.strip():
            close_list()
            i += 1
            continue

        close_list()
        # Merge consecutive paragraph lines
        paras = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith("#") and not lines[i].startswith("```") and not re.match(r"^(\s*)[-*+]\s+", lines[i]) and not re.match(r"^(\s*)\d+\.\s+", lines[i]) and not ( "|" in lines[i] and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:-]+\|", lines[i + 1] or "")):
            if lines[i].startswith("|"):
                break
            paras.append(lines[i])
            i += 1
        out.append(f"<p>{_inline(' '.join(paras))}</p>")

    close_list()
    if in_code:
        body = _escape("\n".join(code_buf))
        out.append(f"<pre><code>{body}</code></pre>")
    return "\n".join(out)


def _table_html(rows: list[str]) -> str:
    def cells(row: str) -> list[str]:
        row = row.strip().strip("|")
        return [c.strip() for c in row.split("|")]

    if len(rows) < 2:
        return ""
    headers = cells(rows[0])
    body_rows = [cells(r) for r in rows[2:] if not re.match(r"^[\s|:-]+$", r)]
    thead = "".join(f"<th>{_inline(h)}</th>" for h in headers)
    tbody = ""
    for row in body_rows:
        # pad/truncate to header width
        while len(row) < len(headers):
            row.append("")
        tbody += "<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row[: len(headers)]) + "</tr>"
    return f'<div class="table-wrap"><table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table></div>'


# --- Data loading -----------------------------------------------------------

def load_evidence(out: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    ev = out / "evidence"
    if not ev.exists():
        return items
    for path in sorted(ev.glob("*.json")):
        data = read_json(path, default={})
        chunk = data if isinstance(data, list) else data.get("items", [])
        for item in chunk or []:
            item = dict(item)
            item["_file"] = path.name
            items.append(item)
    return items


def read_md(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def extract_title(md: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", md, flags=re.M)
    return m.group(1).strip() if m else fallback


# --- HTML pieces ------------------------------------------------------------

CSS = r"""
:root {
  --ink: #12202e;
  --ink-soft: #3a4a5c;
  --muted: #6b7c8f;
  --paper: #f3efe6;
  --paper-2: #e7eef5;
  --panel: rgba(255, 252, 246, 0.92);
  --line: rgba(18, 32, 46, 0.12);
  --accent: #0b7a6e;
  --accent-2: #c45c26;
  --fato: #0b7a6e;
  --inferencia: #b45309;
  --especulacao: #7c3aed;
  --ok: #1a7f4b;
  --warn: #b45309;
  --bad: #b42318;
  --shadow: 0 18px 50px rgba(18, 32, 46, 0.08);
  --radius: 18px;
  --font-display: "Fraunces", "Iowan Old Style", Georgia, serif;
  --font-body: "IBM Plex Sans", "Segoe UI", sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, monospace;
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  color: var(--ink);
  font-family: var(--font-body);
  line-height: 1.55;
  background:
    radial-gradient(1200px 700px at 10% -10%, #d7e7f2 0%, transparent 55%),
    radial-gradient(900px 600px at 100% 0%, #f0dcc8 0%, transparent 50%),
    linear-gradient(160deg, var(--paper-2), var(--paper));
  min-height: 100vh;
}

a { color: var(--accent); }
code, pre { font-family: var(--font-mono); font-size: 0.92em; }
code {
  background: rgba(18,32,46,0.06);
  padding: 0.1em 0.35em;
  border-radius: 6px;
}
pre {
  background: #102033;
  color: #e8eef5;
  padding: 1rem 1.1rem;
  border-radius: 12px;
  overflow: auto;
}
pre code { background: none; padding: 0; color: inherit; }

.shell { max-width: 1120px; margin: 0 auto; padding: 1.25rem 1.25rem 4rem; }

.topbar {
  position: sticky; top: 0; z-index: 40;
  display: flex; gap: 0.75rem; align-items: center; justify-content: space-between;
  padding: 0.7rem 0.9rem;
  margin: 0 0 1.25rem;
  backdrop-filter: blur(14px);
  background: rgba(243, 239, 230, 0.82);
  border: 1px solid var(--line);
  border-radius: 999px;
  box-shadow: var(--shadow);
}
.brand {
  font-family: var(--font-display);
  font-weight: 600;
  letter-spacing: -0.02em;
  white-space: nowrap;
}
.brand span { color: var(--accent); }
.top-actions { display: flex; gap: 0.4rem; flex-wrap: wrap; justify-content: flex-end; }
.top-actions button, .chip-btn {
  appearance: none; border: 1px solid var(--line); background: var(--panel);
  color: var(--ink); border-radius: 999px; padding: 0.35rem 0.75rem;
  font: inherit; font-size: 0.85rem; cursor: pointer;
}
.top-actions button:hover, .chip-btn:hover, .chip-btn.active {
  border-color: var(--accent); color: var(--accent);
}

.hero {
  display: grid;
  grid-template-columns: 1.4fr 0.9fr;
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}
@media (max-width: 860px) {
  .hero { grid-template-columns: 1fr; }
  .topbar { border-radius: 16px; flex-direction: column; align-items: stretch; }
}

.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 1.25rem 1.35rem;
}

.hero h1 {
  font-family: var(--font-display);
  font-size: clamp(1.8rem, 4vw, 2.6rem);
  line-height: 1.1;
  margin: 0 0 0.5rem;
  letter-spacing: -0.03em;
}
.lede { color: var(--ink-soft); margin: 0 0 1rem; max-width: 42ch; }
.meta { display: flex; flex-wrap: wrap; gap: 0.45rem; margin-top: 0.75rem; }
.pill {
  display: inline-flex; align-items: center; gap: 0.35rem;
  border-radius: 999px; padding: 0.28rem 0.7rem;
  font-size: 0.8rem; border: 1px solid var(--line); background: #fff;
}
.pill.ok { color: var(--ok); border-color: color-mix(in srgb, var(--ok) 35%, white); background: color-mix(in srgb, var(--ok) 10%, white); }
.pill.warn { color: var(--warn); border-color: color-mix(in srgb, var(--warn) 35%, white); background: color-mix(in srgb, var(--warn) 10%, white); }
.pill.bad { color: var(--bad); border-color: color-mix(in srgb, var(--bad) 35%, white); background: color-mix(in srgb, var(--bad) 10%, white); }
.pill.neutral { color: var(--muted); }

.gate-grid { display: grid; gap: 0.7rem; }
.gate {
  display: grid; grid-template-columns: 1fr auto; gap: 0.25rem;
  padding: 0.75rem 0.85rem; border-radius: 14px; border: 1px solid var(--line); background: #fff;
}
.gate strong { font-size: 0.92rem; }
.gate small { color: var(--muted); grid-column: 1 / -1; }

.nav-tabs {
  display: flex; flex-wrap: wrap; gap: 0.4rem;
  margin: 0 0 1rem; position: sticky; top: 4.2rem; z-index: 30;
  padding: 0.35rem 0;
  background: linear-gradient(var(--paper), color-mix(in srgb, var(--paper) 70%, transparent));
}
.nav-tabs a {
  text-decoration: none; color: var(--ink-soft);
  padding: 0.4rem 0.8rem; border-radius: 999px; border: 1px solid transparent;
  background: rgba(255,255,255,0.55); font-size: 0.88rem;
}
.nav-tabs a:hover, .nav-tabs a.active {
  color: var(--accent); border-color: color-mix(in srgb, var(--accent) 30%, white);
  background: #fff;
}

section.block { margin-bottom: 1.15rem; scroll-margin-top: 6.5rem; }
section.block h2 {
  font-family: var(--font-display);
  font-size: 1.45rem; margin: 0 0 0.85rem; letter-spacing: -0.02em;
}
.prose :is(h1,h2,h3,h4) { font-family: var(--font-display); letter-spacing: -0.02em; }
.prose h3 { margin-top: 1.4rem; }
.prose p { margin: 0.55rem 0; }
.prose ul, .prose ol { padding-left: 1.2rem; }
.prose li { margin: 0.25rem 0; }
.table-wrap { overflow: auto; margin: 0.8rem 0; border-radius: 12px; border: 1px solid var(--line); }
table { width: 100%; border-collapse: collapse; font-size: 0.92rem; background: #fff; }
th, td { padding: 0.65rem 0.75rem; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
th { background: #f7f3eb; font-weight: 600; }

.toolbar {
  display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;
  margin-bottom: 0.85rem;
}
.toolbar input[type="search"] {
  flex: 1 1 220px; min-width: 180px;
  border: 1px solid var(--line); border-radius: 999px;
  padding: 0.5rem 0.9rem; font: inherit; background: #fff;
}
.filters { display: flex; flex-wrap: wrap; gap: 0.35rem; }

.evidence-list { display: grid; gap: 0.55rem; }
.ev-card {
  border: 1px solid var(--line); border-radius: 14px; padding: 0.8rem 0.95rem; background: #fff;
  display: grid; gap: 0.35rem;
}
.ev-card.hidden { display: none; }
.ev-head { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; }
.ev-id { font-family: var(--font-mono); font-size: 0.8rem; color: var(--muted); }
.label {
  font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em;
  padding: 0.15rem 0.45rem; border-radius: 999px; color: #fff; font-weight: 600;
}
.label.fato { background: var(--fato); }
.label.inferencia { background: var(--inferencia); }
.label.especulacao { background: var(--especulacao); }
.ev-claim { font-weight: 550; }
.ev-support { color: var(--ink-soft); font-size: 0.9rem; }

.chart { display: grid; gap: 0.65rem; margin-top: 0.5rem; }
.bar-row { display: grid; grid-template-columns: minmax(120px, 180px) 1fr; gap: 0.6rem; align-items: center; }
.bar-track {
  height: 28px; border-radius: 999px; background: rgba(18,32,46,0.06);
  overflow: hidden; position: relative;
}
.bar-fill {
  height: 100%; border-radius: 999px;
  background: linear-gradient(90deg, var(--accent), #1aa6a0);
  display: flex; align-items: center; padding: 0 0.7rem;
  color: #fff; font-size: 0.75rem; white-space: nowrap; min-width: 2rem;
}
.bar-meta { font-size: 0.82rem; color: var(--muted); grid-column: 2; }

.details {
  border: 1px solid var(--line); border-radius: 14px; background: #fff; margin: 0.5rem 0;
}
.details summary {
  cursor: pointer; padding: 0.75rem 0.95rem; font-weight: 600; list-style: none;
}
.details summary::-webkit-details-marker { display: none; }
.details[open] summary { border-bottom: 1px solid var(--line); }
.details .inner { padding: 0.75rem 0.95rem 1rem; }

.footer-note {
  margin-top: 1.5rem; color: var(--muted); font-size: 0.85rem; text-align: center;
}

@media print {
  body { background: #fff; }
  .topbar, .nav-tabs, .toolbar, .top-actions { display: none !important; }
  .panel, .ev-card, .details { box-shadow: none; break-inside: avoid; }
  section.block { break-inside: avoid; }
}
"""

JS = r"""
(function () {
  const tabs = [...document.querySelectorAll(".nav-tabs a")];
  const sections = tabs.map(t => document.querySelector(t.getAttribute("href"))).filter(Boolean);

  function setActive() {
    let current = sections[0];
    for (const s of sections) {
      if (s.getBoundingClientRect().top <= 140) current = s;
    }
    tabs.forEach(t => t.classList.toggle("active", t.getAttribute("href") === "#" + current.id));
  }
  window.addEventListener("scroll", setActive, { passive: true });
  setActive();

  const search = document.getElementById("ev-search");
  const chips = [...document.querySelectorAll("[data-filter]")];
  const cards = [...document.querySelectorAll(".ev-card")];
  let activeLabel = "all";

  function applyFilter() {
    const q = (search?.value || "").trim().toLowerCase();
    cards.forEach(card => {
      const label = card.dataset.label || "";
      const hay = card.dataset.search || "";
      const labelOk = activeLabel === "all" || label === activeLabel;
      const textOk = !q || hay.includes(q);
      card.classList.toggle("hidden", !(labelOk && textOk));
    });
    const visible = cards.filter(c => !c.classList.contains("hidden")).length;
    const count = document.getElementById("ev-count");
    if (count) count.textContent = visible + " / " + cards.length;
  }

  chips.forEach(chip => {
    chip.addEventListener("click", () => {
      chips.forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      activeLabel = chip.dataset.filter;
      applyFilter();
    });
  });
  search?.addEventListener("input", applyFilter);
  applyFilter();

  document.getElementById("btn-expand")?.addEventListener("click", () => {
    document.querySelectorAll("details.details").forEach(d => { d.open = true; });
  });
  document.getElementById("btn-collapse")?.addEventListener("click", () => {
    document.querySelectorAll("details.details").forEach(d => { d.open = false; });
  });
  document.getElementById("btn-print")?.addEventListener("click", () => window.print());
})();
"""


def gate_pill(value: Any) -> tuple[str, str, str]:
    if value is True:
        return "ok", "passou", "Gate satisfeito"
    if value is False:
        return "bad", "falhou", "Modo degradado possível"
    return "neutral", "n/d", "Ainda não avaliado"


def sensitivity_chart(data: dict[str, Any]) -> str:
    if not data:
        return '<p class="empty">Sem dados de sensibilidade.</p>'
    if data.get("skipped"):
        reason = _escape(str(data.get("reason") or "pulado"))
        return f'<p class="empty">Sensibilidade pulada: {reason}</p>'
    variables = data.get("variables") or []
    if not variables:
        return '<p class="empty">Nenhuma variável de sensibilidade.</p>'

    rows = ['<div class="chart">']
    for i, var in enumerate(variables):
        name = _escape(str(var.get("name") or f"var-{i}"))
        delta = _escape(str(var.get("delta") or ""))
        notes = _escape(str(var.get("notes") or ""))
        outcome = var.get("outcome_band") or ["?", "?"]
        # visual width from index alternating — decorative, not quantitative claim
        width = 40 + ((i * 17) % 45)
        rows.append(
            f'<div class="bar-row"><div><strong>{name}</strong><div class="bar-meta">{delta}</div></div>'
            f'<div><div class="bar-track"><div class="bar-fill" style="width:{width}%">'
            f'{_escape(str(outcome[0]))} – {_escape(str(outcome[1]))}</div></div>'
            f'<div class="bar-meta">{notes}</div></div></div>'
        )
    rows.append("</div>")
    return "\n".join(rows)


def evidence_section(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<p class="empty">Nenhuma evidência coletada.</p>'

    cards = []
    for item in items:
        label = str(item.get("label") or "especulação")
        label_class = {
            "fato": "fato",
            "inferência": "inferencia",
            "inferencia": "inferencia",
            "especulação": "especulacao",
            "especulacao": "especulacao",
        }.get(label, "especulacao")
        eid = _escape(str(item.get("id") or ""))
        claim = _escape(str(item.get("claim") or ""))
        support = _escape(str(item.get("support") or ""))
        source = _escape(str(item.get("source") or ""))
        conf = _escape(str(item.get("confidence_band") or ""))
        search = _escape(
            f"{eid} {label} {claim} {support} {source} {conf}".lower()
        )
        cards.append(
            f'<article class="ev-card" data-label="{label_class}" data-search="{search}">'
            f'<div class="ev-head"><span class="ev-id">{eid}</span>'
            f'<span class="label {label_class}">{_escape(label)}</span>'
            f'<span class="pill neutral">{source}</span>'
            f'<span class="pill neutral">confiança {conf or "—"}</span></div>'
            f'<div class="ev-claim">{claim}</div>'
            f'<div class="ev-support">{support}</div></article>'
        )

    return f'<div class="evidence-list">{"".join(cards)}</div>'


def wrap_collapsible_md(md: str, open_first: int = 3) -> str:
    """Turn ### headings into <details> for interactivity when many sections."""
    if not md.strip():
        return '<p class="empty">—</p>'
    parts = re.split(r"(?=^###\s+)", md, flags=re.M)
    if len(parts) <= 2:
        return f'<div class="prose">{md_to_html(md)}</div>'

    html_parts: list[str] = []
    preface = parts[0].strip()
    if preface:
        html_parts.append(f'<div class="prose">{md_to_html(preface)}</div>')

    for idx, part in enumerate(parts[1:]):
        m = re.match(r"^###\s+(.+)$", part, flags=re.M)
        title = m.group(1).strip() if m else f"Seção {idx + 1}"
        body = part[m.end() :] if m else part  # type: ignore[union-attr]
        opened = " open" if idx < open_first else ""
        html_parts.append(
            f'<details class="details"{opened}><summary>{_inline(title)}</summary>'
            f'<div class="inner prose">{md_to_html(body)}</div></details>'
        )
    return "\n".join(html_parts)


def build_html(
    *,
    slug: str,
    target: str,
    state: dict[str, Any],
    docs: dict[str, str],
    evidence: list[dict[str, Any]],
    sensitivity: dict[str, Any],
    generated_at: str,
) -> str:
    gates = state.get("gates") or {}
    gate_rows = []
    for key, label in (
        ("evidence_sufficient", "Evidência suficiente"),
        ("backtest_reproduces", "Backtest reproduz falha"),
        ("devil_advocate_holds", "Advogado do diabo"),
    ):
        klass, status, hint = gate_pill(gates.get(key))
        gate_rows.append(
            f'<div class="gate"><strong>{label}</strong>'
            f'<span class="pill {klass}">{status}</span>'
            f"<small>{hint}</small></div>"
        )

    title = extract_title(docs.get("verdict.md", ""), f"Autópsia: {slug}")
    failure_def = _escape(str(state.get("failure_definition") or "inferido do histórico"))
    horizon = _escape(str(state.get("horizon") or "inferido"))
    target_esc = _escape(target)

    sections = [
        ("veredito", "Veredito", "verdict.md", False),
        ("origem", "Origem", "origin.md", False),
        ("hipoteses", "Pré-mortem", "hypotheses.md", True),
        ("julgamento", "Pós-mortem", "judgment.md", True),
        ("simulacao", "Simulação", "simulation.md", False),
        ("premissas", "Premissas", "assumptions.md", False),
    ]

    nav = "".join(f'<a href="#{sid}">{label}</a>' for sid, label, _, _ in sections)
    nav += '<a href="#evidencias">Evidências</a><a href="#sensibilidade">Sensibilidade</a>'

    body_sections = []
    for sid, label, filename, collapsible in sections:
        raw = docs.get(filename, "")
        content = wrap_collapsible_md(raw) if collapsible else f'<div class="prose">{md_to_html(raw)}</div>'
        body_sections.append(
            f'<section class="block panel" id="{sid}"><h2>{label}</h2>{content}</section>'
        )

    facts = sum(1 for e in evidence if e.get("label") == "fato")
    body_sections.append(
        f'''<section class="block panel" id="evidencias">
        <h2>Evidências</h2>
        <div class="toolbar">
          <input id="ev-search" type="search" placeholder="Buscar evidência, id, suporte…" />
          <div class="filters">
            <button type="button" class="chip-btn active" data-filter="all">Todas</button>
            <button type="button" class="chip-btn" data-filter="fato">Fatos</button>
            <button type="button" class="chip-btn" data-filter="inferencia">Inferências</button>
            <button type="button" class="chip-btn" data-filter="especulacao">Especulações</button>
          </div>
          <span class="pill neutral" id="ev-count">{len(evidence)} / {len(evidence)}</span>
          <span class="pill neutral">{facts} fatos</span>
        </div>
        {evidence_section(evidence)}
        </section>'''
    )

    body_sections.append(
        f'<section class="block panel" id="sensibilidade"><h2>Sensibilidade</h2>'
        f"{sensitivity_chart(sensitivity)}</section>"
    )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="shell">
  <header class="topbar">
    <div class="brand">Project <span>Autopsy</span></div>
    <div class="top-actions">
      <button type="button" id="btn-expand">Expandir seções</button>
      <button type="button" id="btn-collapse">Recolher</button>
      <button type="button" id="btn-print">Imprimir / PDF</button>
    </div>
  </header>

  <div class="hero">
    <div class="panel">
      <h1>{_escape(title)}</h1>
      <p class="lede">Relatório frio e blameless do pipeline de autópsia — veredito, causa, contrafactuais e evidências navegáveis.</p>
      <div class="meta">
        <span class="pill">slug: {_escape(slug)}</span>
        <span class="pill">alvo: {target_esc}</span>
        <span class="pill">horizonte: {horizon}</span>
        <span class="pill">fracasso: {failure_def}</span>
        <span class="pill neutral">gerado: {_escape(generated_at)}</span>
      </div>
    </div>
    <div class="panel">
      <h2 style="font-family:var(--font-display);font-size:1.15rem;margin:0 0 0.75rem">Gates</h2>
      <div class="gate-grid">{''.join(gate_rows)}</div>
    </div>
  </div>

  <nav class="nav-tabs">{nav}</nav>
  {''.join(body_sections)}

  <p class="footer-note">Gerado por project-autopsy · artefatos em autopsy/{_escape(slug)}/ · labels: fato / inferência / especulação</p>
</div>
<script>{JS}</script>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    out = Path(args.out).expanduser().resolve()
    if not out.exists():
        print(f"ERROR: missing output dir {out}")
        return 2

    state = read_json(out / "state.json", default={}) or {}
    slug = str(state.get("slug") or out.name)
    target = str(state.get("target") or "")

    docs = {
        name: read_md(out / name)
        for name in (
            "verdict.md",
            "origin.md",
            "hypotheses.md",
            "judgment.md",
            "simulation.md",
            "assumptions.md",
        )
    }
    evidence = load_evidence(out)
    sensitivity = read_json(out / "sensitivity.json", default={}) or {}
    generated_at = utc_now()

    html_doc = build_html(
        slug=slug,
        target=target,
        state=state,
        docs=docs,
        evidence=evidence,
        sensitivity=sensitivity,
        generated_at=generated_at,
    )

    ensure_dir(out)
    local_path = out / "report.html"
    local_path.write_text(html_doc, encoding="utf-8")
    print(f"wrote {local_path}")

    desktop_path = None
    desktop_error = None
    if not args.no_desktop:
        stamp = datetime.now().strftime("%Y%m%d-%H%M")
        candidate = desktop_dir() / f"autopsy-{slug}-{stamp}.html"
        try:
            candidate.write_text(html_doc, encoding="utf-8")
            desktop_path = candidate
            print(f"wrote {desktop_path}")
        except OSError as exc:
            desktop_error = str(exc)
            print(f"WARN: could not write Desktop copy ({desktop_error})")
            print(f"WARN: open local report instead: {local_path}")

    meta = {
        "report_html": str(local_path),
        "desktop_html": str(desktop_path) if desktop_path else None,
        "desktop_error": desktop_error,
        "generated_at": generated_at,
    }
    write_json(out / "report_export.json", meta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
