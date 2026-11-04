# Comparação de métricas e baselines

As definições foram registradas em `docs/decisions.md` antes deste cálculo. Este relatório
usa o mesmo gold isolado de 100 reviews, as mesmas 30 perguntas e relevâncias congeladas.
Não houve ajuste de limiar nem mudanças nos dados. Anotações de IA continuam pendentes
de revisão humana independente; este é um conjunto de desenvolvimento, não teste final.

## Protocolo

As quatro métricas são médias macro das 24 perguntas respondíveis. Recall limitado é
`acertos / min(k, total de relevantes)`; precision é `acertos / k`, incluindo posições
vazias. Hit é a presença de ao menos um relevante; MRR usa a primeira posição relevante.
O recall clássico permanece separado no JSON. Não se deve comparar o recall limitado
com o recall clássico do relatório anterior como se fossem a mesma métrica.

A tabela principal não corta por score em nenhum método. O semântico usa cosseno exato
sobre os 100 documentos, isolando os embeddings da aproximação ANN. Portanto não mede
latência nem recall do índice HNSW. Os rankings para k menores são prefixos do mesmo ranking.
O lexical conta termos distintos compartilhados, com normalização de acentos/case e uma
lista fixa de stopwords, sem treinamento. Empates, inclusive score zero, usam o ID.
O aleatório faz 200 permutações sem reposição, seeds 42..241, no mesmo conjunto elegível.
As tabelas exibem médias; os desvios padrão entre repetições constam no JSON. São variação
do sorteio, não intervalos de confiança sobre a população de perguntas.

## Sem filtros

| Método | k | Hit@k | Recall limitado@k | MRR@k | Precision@k |
| --- | ---: | ---: | ---: | ---: | ---: |
| Aleatório (média de 200) | 1 | 0.023 | 0.023 | 0.023 | 0.023 |
| Aleatório (média de 200) | 3 | 0.070 | 0.034 | 0.043 | 0.024 |
| Aleatório (média de 200) | 5 | 0.117 | 0.053 | 0.054 | 0.024 |
| Aleatório (média de 200) | 8 | 0.179 | 0.083 | 0.063 | 0.024 |
| Palavras-chave | 1 | 0.083 | 0.083 | 0.083 | 0.083 |
| Palavras-chave | 3 | 0.292 | 0.243 | 0.181 | 0.139 |
| Palavras-chave | 5 | 0.417 | 0.335 | 0.212 | 0.108 |
| Palavras-chave | 8 | 0.500 | 0.416 | 0.226 | 0.099 |
| Semântico multilíngue | 1 | 0.167 | 0.167 | 0.167 | 0.167 |
| Semântico multilíngue | 3 | 0.333 | 0.181 | 0.229 | 0.111 |
| Semântico multilíngue | 5 | 0.417 | 0.251 | 0.250 | 0.100 |
| Semântico multilíngue | 8 | 0.500 | 0.335 | 0.263 | 0.073 |

## Com filtros de restaurante, item e data

| Método | k | Hit@k | Recall limitado@k | MRR@k | Precision@k |
| --- | ---: | ---: | ---: | ---: | ---: |
| Aleatório (média de 200) | 1 | 0.345 | 0.345 | 0.345 | 0.345 |
| Aleatório (média de 200) | 3 | 0.700 | 0.517 | 0.503 | 0.295 |
| Aleatório (média de 200) | 5 | 0.836 | 0.635 | 0.534 | 0.251 |
| Aleatório (média de 200) | 8 | 0.930 | 0.795 | 0.548 | 0.218 |
| Palavras-chave | 1 | 0.333 | 0.333 | 0.333 | 0.333 |
| Palavras-chave | 3 | 0.708 | 0.590 | 0.507 | 0.347 |
| Palavras-chave | 5 | 0.833 | 0.678 | 0.534 | 0.267 |
| Palavras-chave | 8 | 0.958 | 0.833 | 0.555 | 0.224 |
| Semântico multilíngue | 1 | 0.542 | 0.542 | 0.542 | 0.542 |
| Semântico multilíngue | 3 | 0.833 | 0.639 | 0.660 | 0.375 |
| Semântico multilíngue | 5 | 0.958 | 0.819 | 0.689 | 0.342 |
| Semântico multilíngue | 8 | 1.000 | 0.948 | 0.696 | 0.271 |

## Cortes operacionais e abstenção

Além do ranking sem limiar, o JSON reporta todas as métricas nos quatro k com corte
semântico `>= 0.25` e lexical `> 0`. Não são escalas de confiança equivalentes.
O aleatório não tem corte de confiança. Abstenção correta e falsa aceitação de evidência
usam somente as seis perguntas sem resposta. Retornar qualquer documento conta como
falsa aceitação, mesmo que um LLM pudesse se abster posteriormente.

| Modo | Método | Abstenção correta | Falsa aceitação |
| --- | --- | ---: | ---: |
| sem_filtro | Palavras-chave > 0 | 1/6 | 5/6 |
| sem_filtro | Semântico >= 0.25 | 0/6 | 6/6 |
| com_filtro | Palavras-chave > 0 | 3/6 | 3/6 |
| com_filtro | Semântico >= 0.25 | 2/6 | 4/6 |

As taxas desta tabela são iguais nos quatro k porque dependem de existir ao menos
um candidato acima do corte, e não de quantos outros documentos ocupam o prefixo.

## Leitura dos resultados

Com filtros, o semântico melhora a ordenação: Hit@1 de 0,542 contra 0,333 lexical e
0,345 aleatório. Em k=8, Hit semântico chega a 1,000 sem corte, mas o aleatório já
atinge 0,930: filtros restritivos deixam poucos candidatos, e vários acabam no top-8.
Isso não prova falha do embedding. MRR e precision revelam melhor a qualidade de ordenação.

Sem filtros, o semântico melhora Hit@1/MRR em relação ao lexical, mas perde em recall
limitado e precision em k=8. Não há superioridade semântica uniforme. A proximidade de
elogios e críticas sobre o mesmo assunto continua difícil; metadados ausentes do texto
da review também prejudicam o modo sem filtro. Abstenção semântica permanece inadequada.

Próximo experimento: combinar rankings lexical e semântico, por exemplo com fusão de
ranks, e avaliar a busca híbrida no mesmo protocolo. Não implementamos nem presumimos
esse ganho aqui. Ajustes de pesos ou limiar exigirão outro conjunto reservado para a métrica final.

## Coleção histórica em inglês

O caminho configurado `data/chroma` não contém banco. A inspeção SQLite somente para
leitura dos bancos não temporários em `data/` e `work/` encontrou apenas coleções
multilíngues em `chroma-smoke`, `embedding-module-smoke`, `pipeline-long-smoke` e
`pipeline-rag-smoke`. `split-collection-check` contém apenas uma coleção sem identidade
de modelo. Diretórios de pytest e cache de modelos foram excluídos da inspeção.
Não foi encontrada coleção histórica com embedding inglês; a ablação não foi executada.
Nenhuma coleção foi modificada. O inventário desta execução consta no relatório JSON.

## Reproduzir

```powershell
$env:SENTENCE_TRANSFORMERS_HOME = "$PWD\work\hf-cache\sentence-transformers"
$env:HF_HUB_OFFLINE = '1'
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py --eval-dir data/eval --compare-baselines --output work/evaluation/comparison.json
.\.venv\Scripts\python.exe -m pytest tests/test_retrieval_baselines.py -v
Remove-Item Env:SENTENCE_TRANSFORMERS_HOME
Remove-Item Env:HF_HUB_OFFLINE
```

O modo comparação fixa os quatro k e os cortes operacionais. Não aceita `--k` ou
`--min-score`; o modo anterior continua disponível sem `--compare-baselines`.
O modelo deve estar em cache: não há downloads automáticos. O JSON registra a revisão
do modelo, versões do runtime, hashes do eval set, rankings e os desvios do aleatório.
Os bancos do projeto não são abertos pelo cálculo exato da comparação.

Os comandos desta reprodução histórica fixam v1 com `--eval-dir data/eval`. O padrão atual sem essa opção é `data/eval/human-v2`.
