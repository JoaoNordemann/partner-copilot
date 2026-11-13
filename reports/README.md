# Relatórios e experimentos

- [Resultados consolidados](final-results-v1/RESULTADOS.md). Na raiz, execute
  `python scripts/build_results.py --check` para validar as tabelas e a proveniência.
- [Retrieval human-v2](human-v2/). As comparações e a calibração usam perguntas
  sintéticas de desenvolvimento já vistas. Prompt e parser não se aplicam.
  Consulte o [protocolo de métricas](../docs/decisions.md).
- [Ablações A–C](generation-kaggle-v2/). A reaplica parser v2 às saídas do prompt
  v1. B executa prompt v2 com parser v1. C revalida B com parser v2. Todas
  reutilizam as perguntas de desenvolvimento. Para repetir, siga as células
  correspondentes no [notebook v2](../notebooks/partner-copilot-v2.ipynb).
- [Geração final](final-v3/README.md). Prompt e parser v3, com perguntas
  contaminadas separadas das originalmente limpas.
- [Benchmark na T4](mistral-t4-v1/README.md). Prompt e parser v3, com reprodução
  do resumo a partir dos registros da sessão.
- [Filtro por aspecto](absa-retrieval-v1/README.md). Análise exploratória em
  corpus sintético, sem geração. O relatório descreve como repetir em CPU.
