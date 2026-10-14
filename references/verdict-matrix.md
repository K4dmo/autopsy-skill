# Verdict Matrix

Classify the project in exactly one cell:

|  | Execução boa | Execução ruim |
|--|--------------|---------------|
| **Origem sólida** | Morto por fator externo | Tinha potencial, desperdiçado |
| **Origem falha** | Bem executado, inviável | Falha sobredeterminada |

## Definitions

- **Origem sólida**: problema real, ICP identificável, timing/canal plausíveis, unit economics não absurdos a priori.
- **Origem falha**: problema fraco, ICP incoerente, mercado inexistente/fechado, tese auto-contraditória.
- **Execução boa**: entregou o essencial no horizonte, aprendeu com sinais, não abandonou por desorganização.
- **Execução ruim**: gaps longos, pivôs sem evidência, qualidade/ops insuficientes, burn sem aprendizado.

## Degraded / special classes

- **Indeterminado**: evidência insuficiente ou fator externo não modelável. Prefer over a forced cell.
- **Causa provável** (not root cause): devil-advocate gate failed; keep classification tentative.

## Report must include

1. Classification (cell or indeterminado)
2. Root cause (≠ symptom)
3. Contributing causes ranked by impact band
4. Point of no return (date/band + evidence)
5. Confidence per conclusion (`baixa` | `média` | `alta`) with citations
