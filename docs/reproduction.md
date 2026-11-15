# Reprodução

Execute os comandos na raiz de um clone com histórico Git. As verificações leem artefatos existentes. Grave novas execuções em caminhos novos para preservar hashes e resultados históricos.

| Resultado | Comando ou roteiro | Recurso |
| --- | --- | --- |
| Tabelas consolidadas e trecho gerado do README | `python scripts/build_results.py --check --update-readme` | CPU, Python padrão e Git. Verifica os insumos contra o commit citado no manifesto. |
| Nova cópia das tabelas | `python scripts/build_results.py --output-dir reports/final-results-reproduced` | CPU. Use um diretório ainda inexistente. |
| Funil e falhas históricas de geração | `python scripts/summarize_generation_history.py --output reports/generation-retrospective-v1/metrics-recheck.json` | CPU. Agrega saídas arquivadas, sem inferência. |
| Filtro por aspecto | `python scripts/evaluate_absa_retrieval.py --output reports/aspect-recheck.json` | CPU, encoder e predições congeladas. Análise exploratória em perguntas já vistas. |
| Resumo FP16, NF4 e HTTP | `python scripts/summarize_gpu_benchmark.py reports/mistral-t4-v1` | CPU, lê os registros da T4. |
| Casos históricos da demo | `python scripts/build_demo_examples.py --check` | CPU. Confere os registros e o corpus de origem. |
| Nova execução do Mistral ou treino e avaliação QLoRA | [Notebooks e protocolos](../notebooks/README.md) | GPU. Fixe o commit, o modelo, o prompt, o parser e o conjunto do protocolo. Confira o saldo e reserve um teto de sessão antes de usar a cota limitada do Kaggle. |

As rodadas de geração e de treino publicadas são históricas. Os JSONL e manifestos preservam as saídas, os conjuntos e a proveniência. Uma execução nova pode produzir saídas diferentes mesmo com decodificação gulosa. As perguntas usadas em iterações continuam marcadas como contaminadas. [Manifesto consolidado](../reports/final-results-v1/manifest.json) · [Índice de experimentos](../reports/README.md) · [Avaliação externa B2W](absa-external-evaluation.md)
