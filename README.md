# PartnerCopilot

[![CI](https://github.com/JoaoNordemann/partner-copilot/actions/workflows/retriever-unit.yml/badge.svg)](https://github.com/JoaoNordemann/partner-copilot/actions/workflows/retriever-unit.yml)

<!-- BEGIN GENERATED RESULTS -->
- RAG de reviews sintéticas, com citações verificadas e abstenção; sem dados reais do iFood.
- Retrieval: recall limitado@5 sem filtro de 0,2514 no multilíngue e 0,2583 no inglês; 4V/16E/4D em 24 perguntas respondíveis expostas.
- Geração v3: 6/9 saídas aceitas, incluindo duas abstenções; 3/4 substantivas aceitas sustentadas e pertinentes na leitura de IA.
- Retry descartado: 25 chamadas extras, 0 rejeições recuperadas; formato válido não garante resposta correta.
- Evidência limitada: corpus conhecido, amostras pequenas e revisão humana assistida; pesos integrais FP16 ainda pendentes.

[Resultados, tabelas e limitações](reports/final-results-v1/RESULTADOS.md).
<!-- END GENERATED RESULTS -->

[API HTTP](docs/api.md) · [Instalação e uso](docs/project-guide.md) · [Decisões](docs/decisions.md) · [Medições pendentes](docs/future-measurements.md)


[Container CPU e caminho GPU](docs/docker.md): receita CPU com fake/replay,
índice criado no primeiro uso e sem pesos/segredos embutidos. **Build e execução
Docker não testados localmente (Docker ausente); caminho GPU também não testado.**
