# Evidência no contexto: análise derivada da v1

Fonte: `generation-kaggle-v1.jsonl`. Os artefatos originais não foram alterados.

Critério fixo: uma pergunta respondível tem evidência no contexto quando ao menos um ID de `relevant_ids` está em `context_ids`, as reviews realmente enviadas ao LLM (até cinco). O denominador inclui todas as 24 respondíveis, inclusive retrieval vazio. IDs de relevância foram conferidos com `data/eval/human-v2/questions.jsonl`.

**Resultado: 22/24 (91,7%) com ao menos uma review rotulada relevante no contexto.** No conjunto recuperado, antes do corte para cinco, são 23/24 (95,8%). Não confundir essa métrica com recall de todas as fontes ou com prova de que a resposta foi factualmente correta. A validade depende também dos julgamentos de relevância existentes.

| Pergunta | Evidência no contexto | IDs relevantes enviados |
| --- | --- | --- |
| q01 | não | nenhum |
| q02 | sim | rev_002257 |
| q03 | sim | rev_001339 |
| q04 | sim | rev_000400, rev_001212 |
| q05 | sim | rev_001123 |
| q06 | sim | rev_001051, rev_001760 |
| q07 | sim | rev_000351, rev_001172, rev_001416, rev_002417 |
| q08 | sim | rev_002833 |
| q09 | sim | rev_000212 |
| q10 | sim | rev_002237 |
| q11 | sim | rev_002289 |
| q12 | sim | rev_002675 |
| q13 | não | nenhum |
| q14 | sim | rev_000813, rev_001076 |
| q15 | sim | rev_001685, rev_002089 |
| q16 | sim | rev_001998 |
| q17 | sim | rev_000934, rev_001552 |
| q18 | sim | rev_000267, rev_002959 |
| q19 | sim | rev_000673, rev_001661 |
| q20 | sim | rev_001998, rev_002142, rev_002494, rev_002675 |
| q21 | sim | rev_002355 |
| q22 | sim | rev_001051, rev_002234, rev_002684 |
| q23 | sim | rev_001265 |
| q24 | sim | rev_001715 |

## Falhas antes da geração

- q01: a relevante `rev_001661` foi recuperada na posição 6 e ficou fora do contexto de cinco. É perda por seleção de contexto, não falha exclusiva do modelo.
- q13: retrieval vazio; a fonte relevante não chegou ao contexto e o LLM não foi chamado. O relatório de retrieval anterior mostra scores abaixo de 0,25.
- Nas outras 22 respondíveis, havia ao menos uma fonte rotulada relevante no contexto, mas todas as saídas foram rejeitadas pelo contrato. Disponibilidade de evidência e conformidade de saída são dimensões separadas.

## Erros de contrato

- 19: `Abstention marker must be the complete output`.
- 5: `Every output line must end with a source citation`.
- Total desse grupo: 24. As 3 ocorrências de `invalid_citation` são um grupo separado; o Counter sem filtro mostra ambos.

## Revisão humana antes da v2

A revisão continua pendente. Copie o arquivo de revisão original para um arquivo novo de revisão humana, preencha seu nome e origem humana, e registre por pergunta se há apoio factual, se a abstenção é adequada e se as citações sustentam as afirmações. Não marque o arquivo original como revisado retroativamente.

Perguntas selecionadas: q01, q09, q13, q22, q25, q26, q27, q28, q29 e q30. Julgue primeiro o contexto recebido pelo LLM, distinguindo a presença de evidência no dataset da presença no contexto. q01 e q13 têm relevância no dataset, mas não recebem essas fontes no contexto.

Nenhum prompt ou parser v2 foi criado nesta análise. Depois da leitura humana, cada mudança deve ser versionada e medida separadamente. A v2 será adaptação após observar a v1 nas mesmas 30 perguntas, não avaliação independente.
