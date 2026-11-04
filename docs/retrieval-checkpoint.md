# Revisão dos resultados de retrieval

No baseline operacional com k=8 e min_score=0,25, com filtros, **4/6 perguntas sem
resposta retornaram documentos** (q25–q28); **1/24 respondíveis teve recall@8 zero**
(q13). Os cinco casos analisados são todos os casos de perda máxima, não um recorte
de um empate maior. Sem filtros, os números são respectivamente 6/6 e 12/24.

## O achado central

Uma evidência correta de atraso (q13, rev_002234) pontua 0,189; o melhor candidato
dessa pergunta pontua 0,210 e não é relevante. Em contraste, os melhores candidatos
de q25 e q27, que não têm resposta nos dados, pontuam 0,584 e 0,515. Um limiar que
rejeitasse esses dois negativos necessariamente rejeitaria também q13. A separação
perfeita por um único score máximo é impossível nestes exemplos observados.

O filtro restringe candidatos por metadados, sem aumentar ou recalibrar o cosseno.
Pode deixar apenas textos do domínio, mas não garante score alto. A hipótese de
confusão entre proximidade temática e suporte factual é coerente com a leitura dos
resultados, não uma demonstração do mecanismo interno do modelo.

## Tabelas completas

Ranking sem corte, sobre o mesmo corpus:

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

O recall das tabelas é limitado: acertos/min(k,total de relevantes). São médias
macro das 24 respondíveis; o aleatório é média de 200 repetições. As tabelas de
ranking **não aplicam min_score**. Por isso Hit@8 com filtros é 24/24 no ranking
sem corte, mas 23/24 no baseline operacional com corte. O embedding usa cosseno
exato no comparativo; o baseline operacional foi executado via Chroma.

## Distribuição do melhor score antes do corte

Os dois negativos estruturais sem candidatos têm score ausente com filtros e não
entram nos quantis; não foram substituídos por zero.

| Modo | Grupo | Perguntas | Sem candidato | Min | Q1 | Mediana | Q3 | Max |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Com filtros | Respondíveis | 24 | 0 | 0.210 | 0.346 | 0.442 | 0.567 | 0.674 |
| Com filtros | Sem resposta | 6 | 2 | 0.287 | 0.383 | 0.465 | 0.532 | 0.584 |
| Sem filtros | Respondíveis | 24 | 0 | 0.265 | 0.404 | 0.475 | 0.578 | 0.723 |
| Sem filtros | Sem resposta | 6 | 0 | 0.355 | 0.466 | 0.518 | 0.574 | 0.748 |

## Revisão textual e circularidade

As dez perguntas da auditoria são q01, q02, q03, q04, q09, q10, q14, q17, q19 e q22.
Elas foram reinspecionadas por IA, com exemplos relevantes e controles negativos.
Os cinco casos de falha têm leituras detalhadas em retrieval-failure-analysis.md.
**Revisão humana independente: 0 perguntas confirmadas.** Não marcamos a leitura
de IA como humana. O checklist human-review-checklist.md identifica os itens pendentes
para o responsável ler, discordar se necessário e registrar conclusões próprias.

As relevâncias usam o gold anotado às cegas por IA, com regras textuais do guia,
combinado a restaurante/item/data. Os aspectos gerados no raw não são usados como
julgamento. O corpus de avaliação usa os aspectos anotados do gold. Os filtros
não usam aspectos/polaridades: evitamos filtrar pela própria resposta esperada.
A origem pode ser conferida no manifesto e em tests/test_eval_set.py, que compara
IDs, textos, aspectos e escopo contra o gold congelado. O viés de anotação de IA
continua sendo uma limitação, mesmo sem cópia dos rótulos do gerador.

## Calibração e CI

0,287 foi escolhido somente nas 20 perguntas de calibração, com k=8 fixo. As outras
dez não alteraram a escolha, mas todas já eram conhecidas dos baselines anteriores.
Não são teste final independente. Nas dez, a rejeição permaneceu 1/2 e a evidência
relevante caiu de 8/8 para 7/8; o candidato não foi promovido.

Push de f31831b concluído. Workflow Retriever unit tests: completed/success, job
retriever-unit: success, incluindo instalação mínima e execução sem Chroma/modelos.
Execução verificada: https://github.com/JoaoNordemann/partner-copilot/actions/runs/41750165793.

## Próximos experimentos registrados

- Geração de ponta a ponta: q25–q28, usando as fontes recuperadas, para verificar se
  o Mistral responde com abstenção explícita. Registrar contagens e evidências, sem
  confundir taxa de abstenção do LLM com taxa de lista vazia do retriever.
- Review mista em q13: comparar review inteira, segmentação por frase/aspecto e
  fusão lexical, mantendo perguntas, relevâncias e splits. Diluição do sinal é hipótese.
- Reranking e busca híbrida: verificar se aumentam suporte factual e ordenação;
  o ganho sobre os casos atuais deve ser testado em perguntas novas posteriormente.

Esses experimentos não foram executados nesta revisão.
