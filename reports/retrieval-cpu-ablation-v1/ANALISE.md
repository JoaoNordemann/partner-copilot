# Análise das ablações de retrieval em CPU

Rodada completa sobre as 30 perguntas expostas de human-v2: 24 respondíveis e seis negativas. Não houve avaliação de geração, ajuste de limiar ou alteração de defaults. Os rótulos preservam a proveniência assistida do conjunto.

## A hipótese principal não se confirmou

O critério primário foi fixado antes da rodada: recall limitado@5 sem filtros, multilíngue menos inglês. Inglês: 0,2583; multilíngue: 0,2514; diferença: -0,006944. Placar: **4 vitórias, 16 empates, 4 derrotas em 24 respondíveis**. Isso não demonstra superioridade do inglês fora desta amostra; mostra que a previsão direcional não foi corroborada aqui. Não trocar a métrica primária para apresentar ganho.

O multilíngue teve MRR@5 maior (0,2500 contra 0,1882), indicando primeiro relevante mais cedo em média, mas não maior recall limitado@5. Lexical chegou a 0,3347 em recall limitado@5 sem filtros. O embedding não vence lexical em toda métrica.

## Filtro por restaurante

Aqui o filtro é somente restaurant_id, sem item/datas. Resultados históricos com filtros completos não são equivalentes. No recall limitado@5 filtrado, multilíngue=0,7465, inglês=0,4715: **11 vitórias, 12 empates, 1 derrota**. O restaurante reduz muito o espaço elegível. Esse ganho depende do escopo fornecido pelo filtro, não prova qualidade semântica geral.

## Placar multilíngue versus inglês, ranking sem corte

| Filtro | k | Métrica | Vitórias | Empates | Derrotas | Delta médio |
| --- | --- | --- | --- | --- | --- | --- |
| sem_filtro | 1 | recall_capped_at_k | 3 | 20 | 1 | 0.083333 |
| sem_filtro | 1 | mrr_at_k | 3 | 20 | 1 | 0.083333 |
| sem_filtro | 3 | recall_capped_at_k | 4 | 18 | 2 | 0.048611 |
| sem_filtro | 3 | mrr_at_k | 6 | 15 | 3 | 0.076389 |
| sem_filtro | 5 | recall_capped_at_k | 4 | 16 | 4 | -0.006944 |
| sem_filtro | 5 | mrr_at_k | 7 | 12 | 5 | 0.061806 |
| sem_filtro | 8 | recall_capped_at_k | 3 | 16 | 5 | -0.043750 |
| sem_filtro | 8 | mrr_at_k | 9 | 10 | 5 | 0.062550 |
| sem_filtro | 12 | recall_capped_at_k | 4 | 16 | 4 | 0.028819 |
| sem_filtro | 12 | mrr_at_k | 11 | 8 | 5 | 0.069662 |
| restaurante | 1 | recall_capped_at_k | 3 | 20 | 1 | 0.083333 |
| restaurante | 1 | mrr_at_k | 3 | 20 | 1 | 0.083333 |
| restaurante | 3 | recall_capped_at_k | 8 | 14 | 2 | 0.166667 |
| restaurante | 3 | mrr_at_k | 9 | 12 | 3 | 0.138889 |
| restaurante | 5 | recall_capped_at_k | 11 | 12 | 1 | 0.275000 |
| restaurante | 5 | mrr_at_k | 11 | 10 | 3 | 0.149306 |
| restaurante | 8 | recall_capped_at_k | 8 | 15 | 1 | 0.192708 |
| restaurante | 8 | mrr_at_k | 13 | 8 | 3 | 0.132192 |
| restaurante | 12 | recall_capped_at_k | 2 | 22 | 0 | 0.052083 |
| restaurante | 12 | mrr_at_k | 13 | 8 | 3 | 0.123396 |

Todos os demais placares por métrica/k, contra lexical e acaso, nos dois modos e políticas, estão em results.json, inclusive deltas por pergunta. As seis negativas não entram no placar de ranking.

## k: recuperar mais tem custo de ruído

No multilíngue com restaurante, de k=5 para 8 entram 13 relevantes e 59 irrelevantes adicionais, somados nas 24 respondíveis. De 8 para 12 entram seis relevantes e 90 irrelevantes adicionais. Hit já era 24/24 em k=8 e não melhora em 12; precision cai de 0,2708 para 0,2014. O recall clássico sobe de 0,9274 para 1,0000. Isso expõe o custo, mas não fixa um k ótimo sem medir utilidade da geração.

Sem filtro, de k=8 para 12 o multilíngue adiciona sete relevantes e 89 irrelevantes. A precisão média muda de 0,0729 para 0,0729 por coincidência agregada; o volume de ruído aumenta. Recall limitado não precisa ser monotônico ao variar k porque muda o denominador.

O acaso filtrado já alcança hit@12 médio=0,9775; lexical e multilíngue chegam a 1,0000. Assim, acerto com k grande e espaço pequeno é pouco discriminante. A dispersão do acaso entre 200 seeds e os valores por pergunta estão preservados.

## Abstenção não é comprovada por ranking

Sem corte, todos os métodos retornam documentos às seis negativas quando o filtro é somente restaurante ou ausente. Remover item/data elimina as abstenções estruturais anteriores. A política operacional aparece separada no relatório; aplicar 0,25 aos dois embeddings não equivale a calibrar confiança entre modelos. Não ajustar o corte usando esta matriz.

## Reprodução e integridade

Foram reconstruídas duas coleções temporárias isoladas, cada uma com 100 reviews e contrato do próprio embedding. Nenhum vetor foi misturado. Todos os candidatos elegíveis foram recuperados e ordenados por cosseno/ID; isso remove perdas de seleção ANN nesta base pequena, mas não é benchmark de latência do retriever de produção.

Documentos e consultas couberam sem truncamento: inglês, máximos 84/39 tokens, limite 256; multilíngue, 53/28, limite 128. Revisões exatas dos pesos e ambiente constam nos arquivos english.json e multilingual.json; hashes de código/protocolo e dados em protocol.json/results.json. O índice de produção não foi alterado.

```powershell
python scripts/evaluate_retrieval_ablations.py --output-dir reports/retrieval-cpu-ablation-v1-reproduction
```

Esse comando usa cache local. --allow-download permite baixar os pesos públicos. O diretório de saída precisa ser novo; o runner não sobrescreve a rodada. O E5 opcional não foi executado. README.md contém a tabela completa de todas as configurações testadas, sem seleção de vencedora.

Análise redigida por IA; não constitui nova revisão humana de relevância nem avaliação limpa de geração.
