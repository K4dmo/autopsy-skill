# Casos de teste

Preencher com 3 projetos mortos (histórico Git rico). Critério: abandono claro ou falha documentável.

| # | Slug | Alvo (path/URL) | Por que serve | Status |
|---|------|-----------------|---------------|--------|
| 1 | TBD | | | pending |
| 2 | TBD | | | pending |
| 3 | TBD | | | pending |

## Casos inéditos (M6)

| # | Slug | Alvo | Notas |
|---|------|------|-------|
| 4 | TBD | | |
| 5 | TBD | | |

## Como rodar

```bash
# from skill root
# /autopsy /path/to/dead-project
python scripts/collect_git.py --target /path/to/dead-project --out autopsy/<slug>
python scripts/validate_report.py --out autopsy/<slug>
```
