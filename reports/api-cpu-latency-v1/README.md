# Latências isoladas de CPU na integração da API

Rodada única pré-definida: 8 consultas operacionais x 5 repetições, após uma passagem de warm-up. Sem GPU/LLM, sem conjunto reservado. Índice somente do split RAG registrado.

Hardware: {"os": "Windows-11-10.0.26200-SP0", "logical_cpus": 12, "device": "cpu", "cpu_model": "AMD Ryzen 5 5600 6-Core Processor              ", "ram_bytes": 34302070784}.
Modelo: paraphrase-multilingual-MiniLM-L12-v2; revisão: None; documentos: 862. Threads torch: 6; interop: 6.

| Etapa atual em CPU local | n | Mediana ms | Média ms | p95 ms |
| --- | --- | --- | --- | --- |
| embedding_ms | 40 | 13.660 | 13.938 | 15.369 |
| search_ms | 40 | 4.130 | 4.176 | 4.562 |
| embedding_search_ms | 40 | 17.813 | 18.145 | 19.763 |

Carga do embedder excluída das amostras: 30041.754 ms. Indexação e warm-up excluídos.
Busca mede count/query Chroma, filtros/corte e conversão dos documentos. Embedding e busca têm intervalos próprios, sem inferência por subtração. A etapa combinada também é medida diretamente.
São tempos do componente CPUIndex usado pela API, não transporte HTTP ou Mistral. Uma execução local sem carga concorrente controlada não define SLA. Os 40 registros são repetições de oito consultas, não quarenta perguntas independentes.
Versões, hashes e observações individuais em metrics.json; protocolo salvo antes da carga e das amostras. Não foi escolhida a melhor entre rodadas. FP16 permanece pendente.

A revisão do modelo consta como null nos metadados: o encoder não expôs `_commit_hash`. Nome, cache local e versões foram registrados, mas não permitem afirmar um hash de pesos verificado.

[Smoke HTTP real](http-smoke.json): índice e embedder prontos; LLM indisponível sem CUDA; `/health` retornou 503, menus 200 e `/ask` 503 com `model_unavailable`. Nenhuma inferência Mistral foi realizada.
