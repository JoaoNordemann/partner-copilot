# Reexecução sem filtros — revisão humana v2

Nova execução com o modelo multilíngue real em cache, mesmo corpus gold de 100 reviews
e julgamentos human-v2. Não foram aplicadas restrições de restaurante, item ou data no
modo sem filtro. Verificação: todas as 30 perguntas tiveram 100 candidatos elegíveis.
Rankings por cosseno exato, sem corte por score nesta tabela.

| Modo | k | Hit@k | Recall limitado@k | MRR@k | Precision@k |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sem filtro | 1 | 0.1667 | 0.1667 | 0.1667 | 0.1667 |
| Sem filtro | 3 | 0.3333 | 0.1806 | 0.2292 | 0.1111 |
| Sem filtro | 5 | 0.4167 | 0.2514 | 0.2500 | 0.1000 |
| Sem filtro | 8 | 0.5000 | 0.3347 | 0.2629 | 0.0729 |
| Com filtro | 1 | 0.5417 | 0.5417 | 0.5417 | 0.5417 |
| Com filtro | 3 | 0.8333 | 0.6389 | 0.6597 | 0.3750 |
| Com filtro | 5 | 0.9583 | 0.8090 | 0.6889 | 0.3417 |
| Com filtro | 8 | 1.0000 | 0.9483 | 0.6958 | 0.2760 |

As métricas são médias das 24 perguntas respondíveis. Recall limitado usa
acertos/min(k,total de relevantes); precision usa acertos/k.
Em k=8, sem corte, o Hit passa de 12/24 sem filtros para 24/24 com filtros.
Com corte 0,25, o resultado com filtros cai para 23/24; sem filtros permanece 12/24.
Nas seis perguntas sem resposta, o corte deixa passar documentos em 6/6 sem filtro
e 4/6 com filtro. O problema de abstenção permanece.

Sem filtros, palavras-chave alcança recall limitado@8 de 0,416, contra 0,335 do
semântico. O embedding não domina o lexical em todas as métricas.
Os filtros explicam grande parte do ganho de escopo observado. Como restaurante e
data nem sempre aparecem no texto embutido, não é uma decomposição causal isolada
da qualidade linguística do embedding. O corpus de 100 documentos não é o índice RAG
de produção com 862 reviews. A revisão human-v2 foi assistida e historicamente exposta.

Relatório completo, com baselines e scores:
`reports/human-v2/retrieval-comparison-unfiltered-check.json`.

```powershell
$env:SENTENCE_TRANSFORMERS_HOME = "$PWD\work\hf-cache\sentence-transformers"
$env:HF_HUB_OFFLINE = '1'
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py --eval-dir data/eval/human-v2 --compare-baselines --output work/evaluation/unfiltered-check.json
Remove-Item Env:SENTENCE_TRANSFORMERS_HOME
Remove-Item Env:HF_HUB_OFFLINE
```
