# Estudo de Engenharia de IA: status

Atualizado em 2026-11-06 para o fechamento `v0.1-rag-mvp`. Documento criado porque
não havia uma tabela de estudo no repositório. Estados refletem evidências reais,
sem datas de execução fictícias ou aprovação automática de experimentos.

| Frente | Estado | Evidência / próximo passo |
| --- | --- | --- |
| Fundamentos HF e inferência NF4 | Concluído no escopo estudado | PoCs informadas e execuções Kaggle preservadas |
| Schema, configuração e dados sintéticos | Implementado e testado | Testes Pydantic/gerador; data/raw versionado |
| Gold, guia de anotação e splits | Referência humana congelada | 100 reviews anotadas pelo autor com adjudicação assistida e exposição prévia documentada. [Manifesto](../data/gold/human_review_manifest.json) |
| Ingestão e persistência | Implementado e testado | IDs determinísticos, Chroma temporário nos testes, bootstrap CPU verificado |
| Retrieval e baselines | Medido | Com/sem filtros, embeddings, k e placares em RESULTADOS.md |
| Geração v3 e análise de falhas | Medido, com limitações | n12/n15/n16 e rubrica; prompt/parser congelados |
| API | Implementado e testado | Startup, modos, saúde, fila, timeout e testes sem GPU |
| Demo Gradio | Implementado e verificado localmente | HTTP com API fake e inspeção visual; fontes integrais e exemplos gravados |
| Latência CPU isolada | Medida | reports/api-cpu-latency-v1; hardware explícito |
| Docker CPU | Receita e bootstrap prontos; container não verificado | Reservar até uma hora nas janelas de treino QLoRA para iniciar o Docker, construir a imagem e testar o container |
| Replay aprovado | Contrato e testes prontos; catálogo pendente | Até três casos com aprovação humana elegível. Começar pela resposta n17 e pela abstenção n20. A falha n12 fica na aba histórica |
| CI e versão MVP | Implementado; publicação protegida por gate | Tag v0.1-rag-mvp somente após CI remoto verde no mesmo commit; badge do README |
| QLoRA / ABSA | Smoke T4 aprovado | 20 passos, máscara de 100 exemplos e recarga do adapter verificados. Treino completo pendente. [Relatório](../reports/absa-qlora-smoke-v1/README.md) |
| FP16 na T4 16 GB | Pendente | Comparação controlada com NF4, sem afirmar resultado antecipado |
| Space | Adiado | Não bloquear entrega local; distinguir gravação de busca CPU ao vivo |
| Avaliação final reservada | Preservada, não executada | Uma rodada futura, sem ajuste posterior |

## Distribuição das pendências

- **Durante o treino QLoRA:** testar o container CPU nos intervalos de espera da GPU.
- **Na próxima sessão Kaggle que tiver folga:** aproveitar a mesma sessão de outro
  trabalho com GPU para medir fila, validação e latência ponta a ponta do backend real.
  Se a sessão não comportar a coleta completa, registrar a lacuna como limitação.
- **Refatoração e publicação:** priorizar refatoração, README e publicação do projeto.
  A curadoria do MVP tem teto de três entradas de replay aprovadas. Os três exemplos
  históricos já cobrem o roteiro da demo, incluindo a falha conhecida.
- **Space:** manter adiado e reavaliar quando houver tempo e catálogo elegível.

[Resultados e limitações](../reports/final-results-v1/RESULTADOS.md) ·
[Notas da versão](releases/v0.1-rag-mvp.md) · [Decisões](decisions.md)
