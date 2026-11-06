# Custo e latência: consolidação de medições existentes

Nenhum benchmark, inferência ou comparação nova foi executado. Todos os valores abaixo são derivados dos artefatos já preservados. Incluem saídas rejeitadas pelo parser: houve custo de inferência mesmo sem resposta aceita. Fontes, hashes, ambientes completos e valores por chamada estão em metrics.json.

## Referência histórica: smoke v1/q01 na T4

Ambiente: **Kaggle, uma Tesla T4, cuda:0**; Mistral-7B-Instruct-v0.2 com pesos NF4 4-bits e double quantization, compute_dtype=float16. Compute FP16 não significa pesos integrais FP16. Python 3.13.16, torch 2.11.0+cu130, CUDA 13.0, Transformers 5.20.2, bitsandbytes 0.50.2, Accelerate 1.15.0. Commit 5ebe981c36db75f28ddc2e94e319de95e2a77cbf. CPU host Kaggle não registrada. Não atribuir estas medidas ao PC local.

| Medida | Valor | Identidade / fonte |
| --- | --- | --- |
| Geração, sem carga dos pesos | 7.984 s | Kaggle / T4 / v1-q01 smoke |
| Carga inicial do objeto | 87.844 s | Kaggle / T4 / v1-q01 smoke |
| Pico alocado durante inferência | 5.212 GB / 4.854 GiB | Kaggle / T4 / v1-q01 smoke |
| Pico reservado pelo allocator | 5.306 GB | Kaggle / T4 / v1-q01 smoke |
| Tokens de prompt | 1551 | Kaggle / T4 / v1-q01 smoke |
| Tokens gerados | 65 | Kaggle / T4 / v1-q01 smoke |

Os números aproximados 5,2 GB, 8 s, 88 s e 1.550 tokens descrevem este exemplo; não são média nem máximo de todas as respostas. O prompt conta instruções + reviews + template de chat, não somente instruções. Os tokens gerados incluem qualquer texto posterior ignorado ou saída rejeitada.

## Todas as rodadas com chamadas novas

Cada linha é **Kaggle / uma Tesla T4 / NF4 4-bits**. Ambientes por linha são os commits indicados; versões completas, hashes de código e configurações ficam em metrics.json. A e C são replay: zero novas chamadas, sem tempo de parsing registrado. D conta só as 25 correções novas, sem repetir as 27 saídas herdadas de B.

| Rodada / ambiente | N | Geração mediana / média / p95 (s) | Carga (s) | Prompt min / mediana / max | Gerados min / mediana / max | Pico alocado GB / GiB | Pico reservado GB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v1 / T4 / 5ebe981 | 27 | 8.804 / 11.380 / 23.719 | 87.844 | 1132 / 1564 / 1657 | 55 / 97 / 375 | 5.558 / 5.176 | 8.674 |
| B / T4 / 3ec7399 | 27 | 8.692 / 9.013 / 16.880 | 98.657 | 711 / 1143 / 1236 | 18 / 104 / 334 | 4.880 / 4.545 | 6.717 |
| D-corrections / T4 / 9dd7c34 | 25 | 9.873 / 11.595 / 28.488 | 101.240 | 991 / 1499 / 1831 | 60 / 105 / 400 | 5.556 / 5.174 | 7.311 |
| JSON-v1 / T4 / b6c2ed6 | 10 | 6.185 / 7.291 / 14.610 | 99.492 | 638 / 845 / 1020 | 49 / 72 / 210 | 4.689 / 4.367 | 4.878 |
| v3-new / T4 / d03e3ae | 9 | 6.315 / 9.545 / 31.851 | 97.161 | 531 / 854 / 1208 | 44 / 87 / 482 | 4.854 / 4.521 | 5.425 |
| v3-contaminated / T4 / d03e3ae | 27 | 12.912 / 16.788 / 40.641 | 97.161 | 517 / 1093 / 1382 | 46 / 149 / 512 | 5.028 / 4.683 | 7.663 |

Mediana e média são sobre todas as chamadas medidas daquela linha, inclusive a primeira inferência e rejeições. O tempo de geração exclui carga de pesos, mas não equivale a um ensaio só de decode com cache aquecido: inclui template, tokenização, cópia, geração e decode. p95 usa nearest-rank ceil(0,95*N), sem interpolação; amostras pequenas não sustentam SLA. Tokens variam com contexto e saída; não anunciar 8 s como latência universal.

O maior pico alocado da rodada v1 foi **5,558 GB (5,176 GiB)**, superior ao smoke de 5,212 GB. O pico reservado chegou a **8,674 GB (8,078 GiB)**; reservado não é igual ao alocado. GB=10^9 bytes; GiB=2^30 bytes. O pico transitório durante a carga dos pesos não foi medido. Não atribuir toda memória da placa apenas a estes contadores.

V3 nova e contaminada compartilham uma carga de **97,161 s**, não duas. model_load_latency_ms é atributo repetido por pergunta, não tempo pago em cada chamada. Demais cargas não são somadas como tempo total de sessão: faltam identidade explícita de processo e logs de sessão completos.

O latency_ms externo do pipeline pode incluir a primeira carga preguiçosa e outros custos. Em D, o latency_ms da linha final soma histórico de B e correção em outra execução; não é latência contínua. Para D foram usados generation_metrics de attempts com new_inference=true. Não subtrair geração do total para inventar latência de retrieval/embedding.

## Custo computacional registrado

| Rodada / ambiente | Chamadas novas medidas | Tokens de entrada | Tokens gerados | Soma de geração (s), sem carga |
| --- | --- | --- | --- | --- |
| v1 / Kaggle T4 / 5ebe981 | 27 | 40125 | 3614 | 307.249 |
| B / Kaggle T4 / 3ec7399 | 27 | 28758 | 3085 | 243.362 |
| D-corrections / Kaggle T4 / 9dd7c34 | 25 | 35589 | 3283 | 289.873 |
| JSON-v1 / Kaggle T4 / b6c2ed6 | 10 | 8241 | 938 | 72.913 |
| v3-new / Kaggle T4 / d03e3ae | 9 | 7645 | 1172 | 85.901 |
| v3-contaminated / Kaggle T4 / d03e3ae | 27 | 27773 | 5768 | 453.278 |
| Total de chamadas registradas acima, múltiplas sessões T4 | 125 | 148131 | 17860 | 1452.576 |

Não é tempo de sessão, tempo faturável nem custo monetário. Os dois smoke tests são exemplos separados, excluídos destes totais. A/C não adicionam tokens de inferência. Não há preço por token de API aplicável automaticamente a este modelo local. Tarifa, quota e duração da sessão Kaggle não foram registradas: custo financeiro fica não calculado. D consumiu 25 correções sem recuperar rejeições; não foi mantido no pipeline normal.

## CPU local: o que foi e não foi medido

**PC local Windows, execução CPU**; identidade do processador, RAM e número de threads não foram registrados na ablação. Não preencher com hardware da T4 nem consultar a máquina atual e atribuir retroativamente ao experimento. Runtime registrado: Python 3.14.7, torch 2.15.0, Transformers 5.22.1, sentence-transformers 6.2.0, ChromaDB 1.5.9, Pydantic 2.14.2. Base de código 57b2073, com hashes das alterações executadas no protocolo original.

| Medida | Valor | Identidade / escopo |
| --- | --- | --- |
| Ablação completa english | 16.863 s | PC local / CPU não identificada / sentence-transformers/all-MiniLM-L6-v2 / revisão 1110a24 |
| Ablação completa multilingual | 8.255 s | PC local / CPU não identificada / sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 / revisão e8f8c21 |
| Embedding de consulta isolado | Não medido separadamente | PC local / CPU não identificada |
| Busca/retrieval isolado | Não medido separadamente | PC local / CPU não identificada |

Os 16,863 s do inglês e 8,255 s do multilíngue são tempos de **execução inteira por modelo**: resolução/cache/download, carga de modelo/tokenizer, checagens de tokens, criação do banco, embedding/upsert de 100 reviews e 60 consultas (30 perguntas x dois modos), ordenação e métricas. O timer começa após ler o dataset. Estado de cache/download não é igual entre modelos. Não dividir por 30/60 nem usar esses tempos para afirmar que um embedding é mais rápido. O ranking foi exaustivo sobre 100 documentos; não é latência de produção do ANN.

## Pendências declaradas

- Latências isoladas de embedding e retrieval em CPU, com modelo/revisão, processador, RAM, threads, carga versus execução, corpus e percentis definidos antes de medir. Nenhuma nova medição agora.
- Comparação NF4 versus pesos integrais FP16: **pendente**, em ambiente identificado com T4 de 16 GB; não executada nesta consolidação. A viabilidade de memória/folga precisa ser verificada, sem presumir que uma execução FP16 caberá. Não confundir compute_dtype=float16 das rodadas NF4 com este baseline.
- Pico de VRAM durante carga e custo financeiro: sem registro suficiente.

## Proveniência e limites

JSONLs de geração, tentativas D, smoke tests e resultados CPU foram somente lidos. Nenhum arquivo bruto foi alterado. Os hashes permitem conferir a origem; nenhuma hipótese de desempenho foi testada novamente. Os tempos de versões diferentes também refletem prompts, contextos e tokens diferentes: não são ablação causal de velocidade do prompt ou do parser.
