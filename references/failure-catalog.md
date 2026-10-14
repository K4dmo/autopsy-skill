# Failure Catalog

Use as hypothesis seeds for pré-mortem. Each entry is a failure mode, not a conclusion.

## Origin

| ID | Mode | Typical signals |
|----|------|-----------------|
| O1 | Solução sem dor | Features sem usage; pitch genérico |
| O2 | ICP errado | Conversões baixas; churn imediato; "interessante" sem compra |
| O3 | Timing cedo/tarde | Mercado sem orçamento; incumbente já consolidou |
| O4 | Unit economics inviáveis | CAC >> LTV; custo variável explode |
| O5 | Dependência de plataforma | API change; política; lock-in hostil |
| O6 | Tese contraditória | Docs/README prometem X, código entrega Y |

## Execution

| ID | Mode | Typical signals |
|----|------|-----------------|
| E1 | Abandono / gaps longos | Commit drought; issues paradas |
| E2 | Overbuild | Complexidade alta, zero validação |
| E3 | Underbuild | Nunca shippou o núcleo |
| E4 | Qualidade/ops | Bugs crônicos; deploy quebrado; zero testes |
| E5 | Pivot sem evidência | Direção muda sem métrica |
| E6 | Canal inexistente | Produto ok, zero go-to-market |
| E7 | Escopo infinito | Roadmap cresce, nada fecha |

## External

| ID | Mode | Typical signals |
|----|------|-----------------|
| X1 | Choque de mercado | Recessão, pandemic, commodity crash |
| X2 | Regulatório | Ban, compliance bloqueante |
| X3 | Competidor dominante | Entrada de big tech; comoditização |
| X4 | Funding cliff | Capital some; runway zero |

## Ambiguous (prefer indeterminado)

| ID | Mode | Note |
|----|------|------|
| A1 | Founder/pessoas | Out of scope v1 — blameless; convert to process/resource signals only |
| A2 | Dado privado ausente | Gate: baixa confiança |
