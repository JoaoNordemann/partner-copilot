# Notebooks

| Notebook | Fluxo e conjunto |
| --- | --- |
| `partner-copilot.ipynb` | Geração v1, prompt e parser v1, 30 perguntas de desenvolvimento. |
| `partner-copilot-v2.ipynb`, `partner-copilot-D.ipynb` | Ablações de prompt v2 e parsers v1/v2, com e sem retry, nas mesmas 30 perguntas contaminadas. |
| `partner-copilot-JSON.ipynb` | Prompt e parser JSON v1, teste n01–n10 limpo na primeira execução. |
| `partner-copilot-V3.ipynb` | Prompt e parser v3, q01–q30 contaminadas e n11–n20 originalmente limpas. |
| `mistral-t4-benchmark.ipynb` | Prompt e parser v3, repetição dos dois conjuntos na T4. |
| `absa-qlora-smoke.ipynb`, `absa-qlora-train.ipynb`, `partnercopilot-absa-kaggle.ipynb` | Teste de treinamento, treino e demonstração do adapter. Usam o contrato JSON de ABSA, independente do parser RAG. |
| `generation_eval.ipynb`, `partner_copilot_colab.ipynb` | Avaliação e execução interativa. As células de configuração identificam o prompt, o parser e o conjunto selecionados. |

Para reproduzir, abra o notebook correspondente numa sessão limpa, selecione a
GPU indicada e siga as células com o commit e os insumos registrados no relatório
da rodada. Use os segredos da plataforma. Salve novas saídas em outro diretório.

[Índice dos experimentos](../reports/README.md) · [Avaliação ABSA](../reports/absa-eval-checkpoint-253-v1/README.md)
