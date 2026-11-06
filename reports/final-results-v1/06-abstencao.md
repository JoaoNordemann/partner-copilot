# O sistema encontra evidência e se abstém quando necessário?

| Configuração / caso | O que mede | Conjunto / exposição | n | Resultado | Contagens brutas | Limitação |
| --- | --- | --- | --- | --- | --- | --- |
| v1 | Abstenção formal e presença de fonte relevante | q01–q30; contaminado por iterações anteriores | 24 respondíveis; 6 negativas | evidência nas positivas 22/24; recusa indevida formal 1/24 | negativas abstidas 2/6; LLM 0/4 chamadas negativas; 2 sem LLM; erros de contrato 27/30 | Recusas semânticas em saídas rejeitadas ficam fora da taxa formal; lista relevante não comprova fidelidade. |
| C | Abstenção formal e presença de fonte relevante | q01–q30; contaminado por iterações anteriores | 24 respondíveis; 6 negativas | evidência nas positivas 22/24; recusa indevida formal 1/24 | negativas abstidas 2/6; LLM 0/4 chamadas negativas; 2 sem LLM; erros de contrato 25/30 | Recusas semânticas em saídas rejeitadas ficam fora da taxa formal; lista relevante não comprova fidelidade. |
| D | Abstenção formal e presença de fonte relevante | q01–q30; contaminado por iterações anteriores | 24 respondíveis; 6 negativas | evidência nas positivas 22/24; recusa indevida formal 1/24 | negativas abstidas 2/6; LLM 0/4 chamadas negativas; 2 sem LLM; erros de contrato 25/30 | Recusas semânticas em saídas rejeitadas ficam fora da taxa formal; lista relevante não comprova fidelidade. |
| json-v1 | Abstenção formal e presença de fonte relevante | n01–n10; contaminado nesta consolidação retrospectiva | 7 respondíveis; 3 negativas | evidência nas positivas 7/7; recusa indevida formal 0/7 | negativas abstidas 0/3; LLM 0/3 chamadas negativas; 0 sem LLM; erros de contrato 3/10 | Recusas semânticas em saídas rejeitadas ficam fora da taxa formal; lista relevante não comprova fidelidade. |
| v3-old | Abstenção formal e presença de fonte relevante | q01–q30; contaminado por iterações anteriores | 24 respondíveis; 6 negativas | evidência nas positivas 23/24; recusa indevida formal 2/24 | negativas abstidas 6/6; LLM 4/4 chamadas negativas; 2 sem LLM; erros de contrato 13/30 | Recusas semânticas em saídas rejeitadas ficam fora da taxa formal; lista relevante não comprova fidelidade. |
| v3-new | Abstenção formal e presença de fonte relevante | n11–n20; limpo na execução congelada; corpus conhecido/rótulos IA | 7 respondíveis; 3 negativas | evidência nas positivas 7/7; recusa indevida formal 0/7 | negativas abstidas 3/3; LLM 2/2 chamadas negativas; 1 sem LLM; erros de contrato 3/10 | Recusas semânticas em saídas rejeitadas ficam fora da taxa formal; lista relevante não comprova fidelidade. |

Commit dos arquivos de entrada: `1f954b3fa3e73e2d4aca3ae896affd2f6300a6d8`.
Gerador: `scripts/build_results.py`; SHA256 LF `977761362c39f42705713b3de73ed418e447e6b8fd654d19d110116231f0b895`.
Entradas desta tabela:

- [reports/final-v3/generation-v3-contaminated.jsonl](https://github.com/JoaoNordemann/partner-copilot/blob/1f954b3fa3e73e2d4aca3ae896affd2f6300a6d8/reports/final-v3/generation-v3-contaminated.jsonl)
- [reports/final-v3/generation-v3-new.jsonl](https://github.com/JoaoNordemann/partner-copilot/blob/1f954b3fa3e73e2d4aca3ae896affd2f6300a6d8/reports/final-v3/generation-v3-new.jsonl)
- [reports/generation-json-v1/generation-json-v1.jsonl](https://github.com/JoaoNordemann/partner-copilot/blob/1f954b3fa3e73e2d4aca3ae896affd2f6300a6d8/reports/generation-json-v1/generation-json-v1.jsonl)
- [reports/generation-kaggle-D/generation-kaggle-D.jsonl](https://github.com/JoaoNordemann/partner-copilot/blob/1f954b3fa3e73e2d4aca3ae896affd2f6300a6d8/reports/generation-kaggle-D/generation-kaggle-D.jsonl)
- [reports/generation-kaggle-v1/generation-kaggle-v1.jsonl](https://github.com/JoaoNordemann/partner-copilot/blob/1f954b3fa3e73e2d4aca3ae896affd2f6300a6d8/reports/generation-kaggle-v1/generation-kaggle-v1.jsonl)
- [reports/generation-kaggle-v2/generation-kaggle-B-prompt-v2-parser-v1.jsonl](https://github.com/JoaoNordemann/partner-copilot/blob/1f954b3fa3e73e2d4aca3ae896affd2f6300a6d8/reports/generation-kaggle-v2/generation-kaggle-B-prompt-v2-parser-v1.jsonl)
- [reports/generation-kaggle-v2/generation-kaggle-C-parser-v2.jsonl](https://github.com/JoaoNordemann/partner-copilot/blob/1f954b3fa3e73e2d4aca3ae896affd2f6300a6d8/reports/generation-kaggle-v2/generation-kaggle-C-parser-v2.jsonl)
- [reports/generation-retrospective-v1/metrics.json](https://github.com/JoaoNordemann/partner-copilot/blob/1f954b3fa3e73e2d4aca3ae896affd2f6300a6d8/reports/generation-retrospective-v1/metrics.json)
