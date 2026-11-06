# Estudo de Engenharia de IA: status

Atualizado em 2026-11-06 para o fechamento `v0.1-rag-mvp`. Documento criado porque
não havia uma tabela de estudo no repositório. Estados refletem evidências reais,
sem datas de execução fictícias ou aprovação automática de experimentos.

| Frente | Estado | Evidência / próximo passo |
| --- | --- | --- |
| Fundamentos HF e inferência NF4 | Concluído no escopo estudado | PoCs informadas e execuções Kaggle preservadas |
| Schema, configuração e dados sintéticos | Implementado e testado | Testes Pydantic/gerador; data/raw versionado |
| Gold, guia de anotação e splits | Disponíveis com limitações | Revisão assistida, não cega em todos os casos; manifesto e decisões |
| Ingestão e persistência | Implementado e testado | IDs determinísticos, Chroma temporário nos testes, bootstrap CPU verificado |
| Retrieval e baselines | Medido | Com/sem filtros, embeddings, k e placares em RESULTADOS.md |
| Geração v3 e análise de falhas | Medido, com limitações | n12/n15/n16 e rubrica; prompt/parser congelados |
| API | Implementado e testado | Startup, modos, saúde, fila, timeout e testes sem GPU |
| Demo Gradio | Implementado e verificado localmente | HTTP com API fake e inspeção visual; fontes integrais e exemplos gravados |
| Latência CPU isolada | Medida | reports/api-cpu-latency-v1; hardware explícito |
| Docker CPU | Receita e bootstrap prontos; container não verificado | Instalar/iniciar Docker e realizar build/smoke |
| Replay aprovado | Contrato e testes prontos; catálogo pendente | Revisão humana elegível antes de disponibilizar gravações |
| CI e versão MVP | Implementado; publicação protegida por gate | Tag v0.1-rag-mvp somente após CI remoto verde no mesmo commit; badge do README |
| QLoRA / ABSA | Pendente | Preparar treino sem gold e avaliar separadamente |
| FP16 na T4 16 GB | Pendente | Comparação controlada com NF4, sem afirmar resultado antecipado |
| Space | Adiado | Não bloquear entrega local; distinguir gravação de busca CPU ao vivo |
| Avaliação final reservada | Preservada, não executada | Uma rodada futura, sem ajuste posterior |

[Resultados e limitações](../reports/final-results-v1/RESULTADOS.md) ·
[Notas da versão](releases/v0.1-rag-mvp.md) · [Decisões](decisions.md)
