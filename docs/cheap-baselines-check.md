# Baselines sem embeddings na avaliação revisada

Execução dedicada sobre o corpus human-v2: 100 reviews, 24 perguntas respondíveis
e seis sem resposta. Nenhum modelo ou banco foi carregado. O teste de subprocesso
bloqueia imports de Chroma, Torch, Transformers e sentence-transformers.

O aleatório faz 200 permutações uniformes sem reposição, seeds 42..241. O lexical
conta palavras distintas compartilhadas, normalizando caixa, acentos e pontuação e
excluindo a lista fixa de stopwords do protocolo. Empates usam ID. Os rankings desta
comparação não usam corte por score. Os dois métodos respeitam os mesmos filtros
quando habilitados. Recall é acertos/min(k,total de relevantes), precision é acertos/k.
Médias macro nas 24 respondíveis. Desvios do aleatório descrevem variação entre sorteios,
não intervalos de confiança sobre uma população maior de perguntas.

## Sem filtros

| Método | k | Hit@k | Recall limitado@k | MRR@k | Precision@k |
| --- | ---: | ---: | ---: | ---: | ---: |
| Aleatório | 1 | 0.0238 | 0.0238 | 0.0238 | 0.0238 |
| Aleatório | 3 | 0.0712 | 0.0347 | 0.0439 | 0.0245 |
| Aleatório | 5 | 0.1187 | 0.0534 | 0.0547 | 0.0247 |
| Aleatório | 8 | 0.1815 | 0.0825 | 0.0638 | 0.0247 |
| Palavras-chave | 1 | 0.0833 | 0.0833 | 0.0833 | 0.0833 |
| Palavras-chave | 3 | 0.2917 | 0.2431 | 0.1806 | 0.1389 |
| Palavras-chave | 5 | 0.4167 | 0.3347 | 0.2118 | 0.1083 |
| Palavras-chave | 8 | 0.5000 | 0.4160 | 0.2257 | 0.0990 |
| Semântico, referência da execução anterior | 1 | 0.1667 | 0.1667 | 0.1667 | 0.1667 |
| Semântico, referência da execução anterior | 3 | 0.3333 | 0.1806 | 0.2292 | 0.1111 |
| Semântico, referência da execução anterior | 5 | 0.4167 | 0.2514 | 0.2500 | 0.1000 |
| Semântico, referência da execução anterior | 8 | 0.5000 | 0.3347 | 0.2629 | 0.0729 |

## Com filtros

| Método | k | Hit@k | Recall limitado@k | MRR@k | Precision@k |
| --- | ---: | ---: | ---: | ---: | ---: |
| Aleatório | 1 | 0.3469 | 0.3469 | 0.3469 | 0.3469 |
| Aleatório | 3 | 0.7050 | 0.5205 | 0.5062 | 0.2981 |
| Aleatório | 5 | 0.8394 | 0.6351 | 0.5369 | 0.2542 |
| Aleatório | 8 | 0.9315 | 0.7950 | 0.5507 | 0.2216 |
| Palavras-chave | 1 | 0.3333 | 0.3333 | 0.3333 | 0.3333 |
| Palavras-chave | 3 | 0.7083 | 0.5903 | 0.5069 | 0.3472 |
| Palavras-chave | 5 | 0.8333 | 0.6778 | 0.5340 | 0.2667 |
| Palavras-chave | 8 | 0.9583 | 0.8257 | 0.5549 | 0.2240 |
| Semântico, referência da execução anterior | 1 | 0.5417 | 0.5417 | 0.5417 | 0.5417 |
| Semântico, referência da execução anterior | 3 | 0.8333 | 0.6389 | 0.6597 | 0.3750 |
| Semântico, referência da execução anterior | 5 | 0.9583 | 0.8090 | 0.6889 | 0.3417 |
| Semântico, referência da execução anterior | 8 | 1.0000 | 0.9483 | 0.6958 | 0.2760 |

## Interpretação

Com filtros, Hit@8 do aleatório é 0,9315 (desvio padrão 0,0437 entre os 200 sorteios),
palavras-chave acerta 23/24 e o semântico 24/24. A margem do semântico sobre o
lexical é uma pergunta, e sobre o acaso filtrado é pequena nesta métrica. Os filtros
reduzem tanto o conjunto elegível que Hit@8 se torna pouco discriminante.

Hit@1 com filtros mostra melhor o ganho de ordenação: semântico 13/24 (0,5417),
lexical 8/24 (0,3333) e aleatório médio 0,3469. Sem filtros, o semântico e o lexical
empatam em Hit@8 (12/24), enquanto o aleatório médio fica em 0,1815. O semântico
perde para lexical em recall limitado@8 sem filtros (0,3347 contra 0,4160).

Não há superioridade uniforme do embedding. A comparação apoia testar fusão lexical
e semântica e reranking, mantendo a ressalva de corpus pequeno e julgamento assistido.
O semântico é somente referência do relatório já executado com os mesmos hashes;
este comando recalcula apenas aleatório e lexical. Os resultados coincidiram exatamente
com esses dois métodos no relatório completo anterior.

## Reproduzir sem modelo

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_cheap_baselines.py --eval-dir data/eval/human-v2 --output work/evaluation/cheap-baselines.json
.\.venv\Scripts\python.exe -m pytest tests/test_cheap_baselines.py -v
```

Relatório versionável: `reports/human-v2/cheap-baselines.json`. Contém rankings, scores
lexicais, todos os k, taxas operacionais e desvios padrão do aleatório.
