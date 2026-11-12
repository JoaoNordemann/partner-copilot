# Formato válido, fonte válida e conteúdo sustentado coincidem?

| Configuração / caso | O que mede | Conjunto / exposição | n | Resultado | Contagens brutas | Limitação |
| --- | --- | --- | --- | --- | --- | --- |
| v1 | Schema, IDs, trecho, aceitação e conteúdo separados | q01–q30; contaminado por iterações anteriores | 30 perguntas; 27 saídas; 3 sem LLM | schema N/A; parser 0/27; IDs 0/27; literal N/A | sustentadas IA 0/2 lidas; humanas assistidas N/A (0 lidas); humanas sustentadas e pertinentes N/A | Denominadores variam por ramo; sustentação só cobre casos lidos e N/A não significa falha. |
| C | Schema, IDs, trecho, aceitação e conteúdo separados | q01–q30; contaminado por iterações anteriores | 30 perguntas; 27 saídas; 3 sem LLM | schema N/A; parser 2/27; IDs 2/27; literal N/A | sustentadas IA 2/2 lidas; humanas assistidas 2/2 (2 lidas); humanas sustentadas e pertinentes 1/2 | Denominadores variam por ramo; sustentação só cobre casos lidos e N/A não significa falha. |
| D | Schema, IDs, trecho, aceitação e conteúdo separados | q01–q30; contaminado por iterações anteriores | 30 perguntas; 27 saídas; 3 sem LLM | schema N/A; parser 2/27; IDs 4/27; literal N/A | sustentadas IA 2/4 lidas; humanas assistidas 0/2 (2 lidas); humanas sustentadas e pertinentes 0/2 | Denominadores variam por ramo; sustentação só cobre casos lidos e N/A não significa falha. |
| json-v1 | Schema, IDs, trecho, aceitação e conteúdo separados | n01–n10; contaminado nesta consolidação retrospectiva | 10 perguntas; 10 saídas; 0 sem LLM | schema 7/10; parser 7/10; IDs 7/7; literal N/A | sustentadas IA 3/4 lidas; humanas assistidas 0/1 (1 lidas); humanas sustentadas e pertinentes 0/1 | Denominadores variam por ramo; sustentação só cobre casos lidos e N/A não significa falha. |
| v3-old | Schema, IDs, trecho, aceitação e conteúdo separados | q01–q30; contaminado por iterações anteriores | 30 perguntas; 27 saídas; 3 sem LLM | schema 16/27; parser 14/27; IDs 10/11; literal 9/10 | sustentadas IA 1/3 lidas; humanas assistidas 0/1 (1 lidas); humanas sustentadas e pertinentes 0/1 | Denominadores variam por ramo; sustentação só cobre casos lidos e N/A não significa falha. |
| v3-new | Schema, IDs, trecho, aceitação e conteúdo separados | n11–n20; limpo na execução congelada; corpus conhecido/rótulos IA | 10 perguntas; 9 saídas; 1 sem LLM | schema 9/9; parser 6/9; IDs 7/7; literal 4/7 | sustentadas IA 6/9 lidas; humanas assistidas 1/4 (4 lidas); humanas sustentadas e pertinentes 1/4 | Denominadores variam por ramo; sustentação só cobre casos lidos e N/A não significa falha. |

Commit dos arquivos de entrada: `717a338c2cb830735555dc3c5c12d419361e866e`.
Gerador: `scripts/build_results.py`; SHA256 LF `b771e78d9c067e584cd3cfd9561d7d57cbefb5da7f3852c311bf8fb394f336d8`.
Entradas desta tabela:

- [reports/generation-retrospective-v1/ai-review.jsonl](https://github.com/JoaoNordemann/partner-copilot/blob/717a338c2cb830735555dc3c5c12d419361e866e/reports/generation-retrospective-v1/ai-review.jsonl)
- [reports/generation-retrospective-v1/human-review.jsonl](https://github.com/JoaoNordemann/partner-copilot/blob/717a338c2cb830735555dc3c5c12d419361e866e/reports/generation-retrospective-v1/human-review.jsonl)
- [reports/generation-retrospective-v1/metrics.json](https://github.com/JoaoNordemann/partner-copilot/blob/717a338c2cb830735555dc3c5c12d419361e866e/reports/generation-retrospective-v1/metrics.json)
