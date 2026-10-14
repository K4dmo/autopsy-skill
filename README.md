# Project Autopsy

Skill autônoma que une pré-mortem + pós-mortem + simulação contrafactual para explicar por que um projeto de software falhou e se ele tinha potencial.

## Uso

No Cursor / Claude Code, com este diretório disponível como skill:

```text
/autopsy <caminho-do-repo-ou-url>
```

Único input obrigatório: o alvo. Horizonte e definição de fracasso são inferidos. Dúvidas viram entradas em `assumptions.md`.

## Saída

Artefatos em `autopsy/<slug>/`:

- `evidence/*.json` — coleta
- `origin.md` — potencial intrínseco
- `hypotheses.md` — pré-mortem (10–15)
- `judgment.md` — pós-mortem + advogado do diabo
- `simulation.md` / `sensitivity.json` — contrafactuais (se backtest passar)
- `verdict.md` + `assumptions.md` — veredito frio

## Estrutura

Ver `SKILL.md` (orquestrador), `agents/` (papéis), `references/` (contratos e matrizes), `scripts/` (coleta e modelo).

## Scripts

```bash
python scripts/collect_git.py --target <path> --out autopsy/<slug>
python scripts/collect_issues.py --target <path> --out autopsy/<slug>
python scripts/collect_code.py --target <path> --out autopsy/<slug>
python scripts/funnel_model.py --out autopsy/<slug>
python scripts/backtest.py --out autopsy/<slug>
python scripts/sensitivity.py --out autopsy/<slug>
python scripts/validate_report.py --out autopsy/<slug>
```

Requisitos: Python 3.10+, `git` no PATH; `gh` opcional para issues.

## Escopo v1

Dentro: repos Git de software, análise blameless, execução via agent skill.

Fora: previsão exata de mercado, análise de pessoas, dados privados sem acesso, GUI.
