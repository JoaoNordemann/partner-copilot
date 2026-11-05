# Transicao para saida JSON: resultado e limite dos experimentos

C e revalidacao das mesmas respostas brutas de B com parser-v2, sem nova inferencia. D reutiliza C como baseline e faz uma unica chamada corretiva para cada uma das 25 saidas rejeitadas. A origem B usa prompt-v2; v1 usa prompt-v1.

| Variante | Saidas do LLM aceitas pelo parser | Novas chamadas |
| --- | --- | --- |
| v1 | 0/27 | 27 na rodada original |
| A: parser-v2 sobre v1 | 0/27 | 0 |
| B: prompt-v2 e parser-v1 | 0/27 | 27 |
| C: parser-v2 sobre B | 2/27 | 0 |
| D: uma correcao sobre C | 2/27 | 25 |

D trouxe ganho zero de aceitacao. As duas respostas aceitas ja estavam em C. Retry descartado da estrategia e ausente da pipeline normal. O runner e o notebook D ficam como reproducao historica, nao mecanismo de seguranca.

## Aceitacao e conteudo separados

| Caso | Aceita pelo parser | Sustentada e pertinente para a pergunta (leitura por Codex/IA) |
| --- | --- | --- |
| q05 em C/D | sim | sim: tampa solta, apoiada em rev_001123 |
| q23 em C/D | sim | nao: responde embalagem; pergunta era sobre mensagens sem retorno |
| Demais 25 saidas de D | nao | nao inferir do parser; leitura completa por caso pendente |

q23 mostra que fonte existente e JSON/formato valido nao garantem pertinencia factual. q22 ja mostrava inversao de elogio. Nao usar aceitacao como sinonimo de acuracia.

## Classificacao das 25 rejeicoes de D

| Mensagem | Quantidade |
| --- | ---: |
| Citation references a review outside the context | 14 |
| Abstention marker must be the complete output | 6 |
| Every output line must end with a source citation | 5 |

As 14 citacoes invalidas foram reproduzidas pelo parser-v2. Classificacao primaria mutuamente exclusiva, com precedencia ID real fora > ID alterado > lista de IDs > marcador > tag/texto. Mais de um problema pode coexistir na mesma saida; o JSON derivado preserva os indicadores secundarios.

| Categoria primaria | Quantidade |
| --- | ---: |
| Varios IDs do contexto no mesmo colchete | 6 |
| ID alterado ou desconhecido | 2 |
| Marcador em formato de citacao | 4 |
| Tag de bloco / texto nos colchetes | 2 |
| ID de review existente fora das cinco enviadas | 0 |

Barra + underscore ja foi normalizada por parser-v2: sua presenca no texto bruto nao explica por si so uma rejeicao restante. q04 usa rev_1212 em vez de rev_001212; q26 muda rev_ para review_. Sao IDs alterados, nao prova de que inventou uma fonte de conteudo. A busca de existencia considera as 3.000 reviews brutas e os 100 documentos do corpus de avaliacao; todos os IDs numericos rejeitados estao listados abaixo para auditoria.

| Pergunta | Categoria primaria | Tokens rejeitados apos normalizacao |
| --- | --- | --- |
| q01 | Varios IDs do contexto no mesmo colchete | `rev_000294, rev_002549, rev_000650, rev_000673, rev_002980`; `SEM_EVIDENCIA` |
| q02 | Varios IDs do contexto no mesmo colchete | `rev_000799, rev_002257`; `rev_001685, rev_002089`; `SEM_EVIDENCIA` |
| q04 | ID alterado ou desconhecido | `rev_000345, rev_1212`; `SEM_EVIDENCIA` |
| q08 | Marcador em formato de citacao | `SEM_EVIDENCIA` |
| q09 | Tag de bloco / texto nos colchetes | `"Nao ha evidencia sobre reclamos de atraso do Burger do Zé na base de dados fornecida"`; `PERGUNTA_JSON`; `"Nao ha informacao sobre atraso especifico do Burger do Zé nas avaliacoes fornecidas"`; `"Avaliacoes_JSONL"` |
| q10 | Marcador em formato de citacao | `SEM_EVIDENCIA` |
| q14 | Marcador em formato de citacao | `SEM_EVIDENCIA` |
| q15 | Varios IDs do contexto no mesmo colchete | `rev_001685, rev_002089`; `SEM_EVIDENCIA` |
| q17 | Varios IDs do contexto no mesmo colchete | `rev_000934, rev_001552` |
| q18 | Varios IDs do contexto no mesmo colchete | `rev_000267, rev_002302`; `SEM_EVIDENCIA` |
| q20 | Varios IDs do contexto no mesmo colchete | `SEM_EVIDENCIA`; `rev_002675, rev_002494, rev_001998` |
| q24 | Marcador em formato de citacao | `SEM_EVIDENCIA`; `AVALIACOES_JSONL` |
| q26 | ID alterado ou desconhecido | `review_002759, review_001998, review_002142, review_001629, review_002675` |
| q28 | Tag de bloco / texto nos colchetes | `AVALIACOES_JSONL` |

Nenhum ID existente fora do contexto foi encontrado nestes 14 casos. Isso nao prova ausencia de erros factuais ou de IDs alterados; evita chamar indiscriminadamente todas as falhas de alucinacao de fontes.

## Hipotese e honestidade

Os resultados sustentam dificuldade de aderencia ao contrato e falhas de uso da evidencia. Nao isolam tamanho do prompt como causa: faltou uma ablacao que variasse apenas comprimento. O prompt-v2 ja era menor, sem resolver o problema. Mistral 7B e quantizacao permanecem os mesmos; nao afirmar superioridade de outro modelo sem medi-lo.

v1, B, C e D usaram as mesmas 30 perguntas. Os ajustes posteriores nao constituem avaliacao limpa independente. O novo prompt JSON foi congelado antes de dez novas perguntas (tres negativas), usando o mesmo corpus conhecido. Essa e uma checagem adicional de perguntas, nao holdout de documentos nem gold humano independente. Nao iterar o prompt apos ver essas dez respostas sem uma nova versao e outro protocolo.

## Estrategia JSON e proximo teste

partner-copilot-json-v1 pede {"abstem": bool, "afirmacoes": [{"texto": ..., "review_ids": [...]}]}. parser-json-v1 valida com Pydantic e confere cada ID diretamente. O codigo renderiza [id], dispensando citacoes escritas pelo modelo. Nao ha retry ou reparo automatico.

As quatro medidas sao separadas: schema valido; abstencao correta; IDs no contexto; sustentacao factual por leitura. O ultimo campo nasce pendente e nunca e preenchido automaticamente a partir do parser. Se JSON falhar, considerar, em experimento futuro, decodificacao restrita/gramatica, depois outro modelo ou atribuicao de fontes por codigo. Nenhuma dessas alternativas foi executada agora.
