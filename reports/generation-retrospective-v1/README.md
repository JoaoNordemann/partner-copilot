# Consolidação retrospectiva de geração

Somente artefatos existentes; nenhuma nova inferência, variante ou juiz LLM. Rubrica registrada antes da releitura em RUBRICA.md. Contagens automáticas recalculadas pelos parsers congelados e conferidas com a aceitação gravada. Brutos originais preservados.

## Funil com denominadores explícitos

Cada célula numérica é aprovadas/aplicáveis. N/A significa campo inexistente no contrato, não zero. Colunas de suporte referem-se **somente à seleção lida sob a nova rubrica**, não à versão inteira. Todos os números de geração abaixo declaram exposição.

| Experimento e exposição | Saídas LLM / perguntas | Schema | Aceitas pelo parser | IDs corretos | Trechos literais | Sustentadas / lidas IA | Sustentadas e respondem / lidas IA |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v1 — contaminado | 27/30 | N/A | 0/27 | 0/27 | N/A | 0/2 | 0/2 |
| C: prompt-v2/parser-v2 — contaminado | 27/30 | N/A | 2/27 | 2/27 | N/A | 2/2 | 1/2 |
| D: C + correção — contaminado | 27/30 | N/A | 2/27 | 4/27 | N/A | 2/4 | 1/4 |
| JSON v1, n01–n10 — contaminado nesta consolidação | 10/10 | 7/10 | 7/10 | 7/7 | N/A | 3/4 | 3/4 |
| v3, q01–q30 — contaminado | 27/30 | 16/27 | 14/27 | 10/11 | 9/10 | 1/3 | 1/3 |
| v3, n11–n20 — limpo na execução congelada | 9/10 | 9/9 | 6/9 | 7/7 | 4/7 | 6/9 | 6/9 |

Texto livre v1/C/D não tem schema JSON nem campo de trecho literal. IDs nesse contrato são diagnosticados em todos os colchetes, com a normalização somente da versão vigente; uma fonte correta não conserta marcador/tag ou outra citação inválida. D tem 4/27 saídas com IDs sintaticamente presentes e todos no contexto, mas só 2/27 passam o contrato inteiro.

C é replay de B sem inferência. D adicionou 25 chamadas corretivas e recuperou zero rejeições; suas duas aceitas são herdadas de C. Não somar C/D como experimentos de respostas independentes nem chamá-los de versões de prompt.

Nas saídas JSON, IDs são avaliados apenas quando schema é válido e há afirmações; trechos apenas quando todos os IDs estão no contexto. Abstenções não recebem aprovação vazia de IDs/trechos. Por isso a tabela não é uma cadeia monotônica única. Decomposição correta:

- v3 antiga: 27 chamadas → 16 schemas válidos = 5 abstenções + 11 respostas com afirmações → 10 com todos os IDs corretos → 9 com todos os trechos literais. Aceitas: 9 respostas + 5 abstenções = 14/27.
- v3 nova: 9 chamadas → 9 schemas válidos = 2 abstenções + 7 respostas com afirmações → 7 com IDs corretos → 4 com trechos literais. Aceitas: 4 respostas + 2 abstenções = 6/9.

Sem precisar ignorar sufixo, schema v3 válido é 0/27 antiga e 0/9 nova: os primeiros objetos válidos vieram com texto/pontuação posterior. A aceitação segue a regra congelada de primeiro objeto; não equivale a JSON puro.

Casos sem LLM: v1/C/D/v3 antiga têm três cada; v3 nova tem um. São excluídos das colunas do modelo. Nesta releitura, q13-v1 e n18-v3 são dois controles sem LLM, ambos com recusa adequada ao contexto vazio, não acertos do Mistral.

## Leitura de IA: escopo e resultado

Foram relidas 26 unidades (experimento, pergunta): **24 saídas de LLM e dois controles**. A seleção inclui falhas e saídas aceitas deliberadamente; não é amostra aleatória nem acurácia global. Os IDs e justificativas estão em ai-review.jsonl. Não foi feita nova leitura integral das 30 em todas as versões.

Nas seis saídas aceitas da v3 nova, cinco são sustentadas e pertinentes sob a rubrica: n11/n13/n17 e as recusas n19/n20. n12 não é sustentada. Entre as quatro respostas substantivas aceitas são três sustentadas e pertinentes. n14 é sustentada no núcleo, mas rejeitada por transcrição literal. n15 e n16 são parciais no conteúdo, com erros materiais de atribuição/escopo; não contá-las como plenamente corretas.

C/D: q05 e q23 são ambas sustentadas quanto ao fato descrito; só q05 responde à pergunta. Isso é diferente de dizer que q23 é correta para a tarefa.

A rodada v3 nova foi limpa quanto a ajustes usando n11–n20 antes daquela execução. Hoje as perguntas já são conhecidas e não podem ser reutilizadas para novos ajustes com alegação de teste limpo. Corpus conhecido e rótulos assistidos/IA não são gold humano independente. As diferenças entre coortes/modelos de saída não constituem comparação causal controlada.

## Taxonomia de falhas

Categorias podem coexistir na mesma saída. Não somar os totais como número de erros únicos. Os julgamentos semânticos abaixo valem só para casos relidos; diagnóstico de formato/citação tem o escopo integral declarado.

| Categoria | Contagem e escopo | Exemplo e evidência |
| --- | --- | --- |
| Marcador com texto | v1: 19/27; C: 15/27; D: 6/27 como primeiro erro do contrato | v1/q09 nega atraso e termina com marcador dentro de explicação. |
| Linhas sem citação final | v1: 5/27; D: 5/27 como primeiro erro | Conferir mensagens originais no JSONL; não são automaticamente erros factuais. |
| Preâmbulo textual observado | 4/24 saídas relidas: v1/q09, v1/q22, C/q23, D/q23 | v1/q22 começa Based on the given rules; C/q23 começa EXATAMENTE. Contagem da seleção, não varredura exaustiva nem necessariamente erro capturado pelo parser. |
| Sufixo após JSON | JSON v1: 3/10 rejeitadas; v3 antiga: 16/16 primeiros objetos com schema; v3 nova: 9/9 | JSON/n02 acrescenta Fonte; v3/n19 acrescenta explicação em inglês. No JSON v1 é rejeitado; na v3 é ignorado conforme regra. |
| IDs agrupados no mesmo colchete | 6/14 falhas de citação D | D/q01 reúne cinco IDs em um colchete; ver citation-classification.json. |
| Marcador ou delimitador interpretado como citação | 4 + 2 das 14 falhas de citação D | [SEM_EVIDENCIA] e tags como AVALIACOES_JSONL. |
| Corrupção de ID | 2/14 falhas de citação D | rev_1212 omite zeros; review_ substitui rev_ em q26. Zero IDs reais existentes fora do contexto nos 14 casos. |
| Abstenção indevida com evidência presente | v1: 1/2 saídas relidas; D: 2/4; v3 antiga: 1/3 | v1/q09 e D/q09 negam atraso explícito de rev_000212; D/q22 nega críticas de sabor; v3/q21 ignora embalagem mal fechada. q22-v1 é resposta parcial, não a mesma recusa de D. |
| Elogio de outro aspecto usado para sabor | 1/9 saídas relidas da v3 nova | n12 cita Bom custo-benefício e afirma sabor bom; a mesma review diz gosto ruim. |
| Trecho atribuído à review errada | 1/9 saídas relidas da v3 nova | n15 atribui Não valeu a pena a rev_002127; o trecho pertence a rev_002490. |
| Combinação de relatos e inversão de escopo | 1/9 saídas relidas da v3 nova | n16 une refrigeração inadequada de rev_001339 aos fatos de rev_000908; a pergunta pede refrigeração adequada no mesmo relato. |
| Resposta irrelevante aceita | 1/2 aceitas de C e a mesma saída herdada em D | q23 responde tampa solta quando a pergunta é sobre mensagens sem retorno. |
| Invenção de fato | 1/4 saídas relidas do JSON v1 | n09 afirma análise microbiológica inexistente em rev_002142. |
| Trecho não literal | 3/9 saídas v3 nova; quatro trechos apontados | n14: velo/velho; n15: fonte errada; n16: espaço e transcrição/caixa. Uma saída pode falhar em mais de um trecho. |
| Recusa semântica com flag falsa | 1/4 saídas relidas do JSON v1 | n10 diz não haver CNPJ, mas abstem=false. |

Mensagens de erro são classificações de primeira falha; não revelam todos os problemas da resposta. A taxonomia de citação D foi conferida contra o corpus completo e está preservada em ../generation-kaggle-D/citation-classification.json.

## Onde está o gargalo?

Os dados apontam principalmente para **geração fiel à pergunta e às fontes**, com custo adicional do contrato de validação. Retrieval também tem falhas reais, mas não explica a maioria das rejeições:

- v1/C/D: fonte relevante presente em 22/24 respondíveis; q01 perde a fonte pelo corte de contexto e q13 pelo limiar. Mesmo assim C/D aceitam só 2/27 saídas, e uma aceita responde ao assunto errado. O retry custou 25 chamadas e recuperou zero.
- v3 nova: fonte relevante presente em 7/7 respondíveis, primeiro objeto com schema em 9/9 chamadas, mas só 4/7 respondíveis entregam resposta substantiva aceita; apenas 3/7 são também sustentadas e pertinentes na leitura de IA. n12 passa tudo mecânico e falha semanticamente.
- Validação bloqueia 3/7 respondíveis da v3 nova. Em n14 o conteúdo principal está sustentado e a transcrição de um trecho causa falso bloqueio factual; n15/n16 têm também erros semânticos. Não relaxar retrospectivamente o contrato nem chamar toda rejeição de alucinação.
- As três negativas da v3 nova se abstêm corretamente: duas pelo modelo e uma por retrieval vazio. Isso não significa que todas as positivas sejam úteis.

Conclusão limitada a estes artefatos e julgamentos de IA, com confirmação humana assistida nos dez casos selecionados e sem revisão humana integral dos demais: melhorar apenas retrieval ou relaxar parsing não resolve fidelidade e pertinência; a validação é necessária, mas existência de ID/trecho não prova sustentação. Não há isolamento causal de tamanho de prompt, quantização ou capacidade do modelo.

## Revisão de João no chat

Há dez revisões humanas históricas da v1, preservadas com a metodologia original. A nova rubrica tem **10/10 casos lidos por João, com enquadramento assistido**: v3-new/n12, v3-new/n15, v3-new/n16, v3-new/n14, C/q23, C/q05, D/q09, D/q22, json-v1/n09 e v3-old/q21. Concordância com a IA: **10/10** em sustentação, **10/10** em pertinência e **10/10** nos dois eixos conjuntamente. É revisão assistida; dez leituras assistidas não estimam concordância geral nem validam um juiz independente. Não importar automaticamente rótulos antigos nem atribuir novas leituras à pessoa.

A fila de entrevista tem dez unidades, em HUMAN-REVIEW.md e review-cases.json, com pergunta, resposta bruta e todo o contexto. human-review.jsonl contém agora os dez julgamentos transcritos das respostas no chat, preservando as observações e o método por caso. Fila concluída; não há caso pendente nesta seleção. Formato de resposta:

```yaml
caso: v3-new/n12
sustentacao: sustentada | parcial | sem_suporte
responde_pergunta: sim | parcial | nao
abstencao: adequada | indevida | nao_se_aplica
justificativa: explique com suas palavras
```

A IA transcreveu os julgamentos e registrou a concordância por eixo e conjuntamente, com método explícito por caso. Se decidir alterar um julgamento seu, preservar o esclarecimento, sem apagar os rótulos de IA nem os arquivos brutos.

LLM-as-judge não foi executado: a prioridade é revisão humana. Caso autorizado futuramente, medir concordância contra esses mesmos rótulos humanos e declarar vieses de comprimento, auto-preferência e posição, sem confundir juiz com gold.

## Reprodução

```powershell
python scripts/summarize_generation_history.py --output reports/generation-retrospective-v1/metrics-recheck.json
```

Revalida saídas existentes, sem carregar modelo. O arquivo de destino precisa ser novo. Fonte/hash, parser e diagnóstico por pergunta em metrics.json. Não altera nenhuma versão de prompt/parser.


## Resultado da revisão humana assistida concluída

João leu os dez casos da fila com as reviews integrais no chat. A IA ajudou a
enquadrar/transcrever os rótulos; algumas classificações foram confirmadas em mensagem
separada, outras derivadas das evidências destacadas, conforme o registro individual.
Concordância com a leitura de IA: 10/10 em sustentação, 10/10 em pertinência e 10/10
nos dois eixos juntos. Houve exposição aos julgamentos e discussão: não é avaliação
cega nem evidência de qualidade de LLM-as-judge. Nenhum juiz foi executado.

| Caso | Sustentação humana assistida | Responde à pergunta? | Abstenção |
| --- | --- | --- | --- |
| v3-new/n12 | sem_suporte | nao | nao_se_aplica |
| v3-new/n15 | parcial | parcial | nao_se_aplica |
| v3-new/n16 | parcial | nao | nao_se_aplica |
| v3-new/n14 | sustentada | sim | nao_se_aplica |
| C/q23 | sustentada | nao | nao_se_aplica |
| C/q05 | sustentada | sim | nao_se_aplica |
| D/q09 | sem_suporte | nao | indevida |
| D/q22 | sem_suporte | nao | indevida |
| json-v1/n09 | sem_suporte | nao | nao_se_aplica |
| v3-old/q21 | sem_suporte | nao | indevida |

Totais desta seleção: 3 sustentadas, 2 parciais e 5 sem suporte. Duas são simultaneamente
sustentadas e pertinentes (n14-v3 e q05-C). C/q23 é sustentada quanto ao fato descrito,
mas irrelevante para a pergunta. n14 tem conteúdo sustentado e bloqueio literal.
Não extrapolar estes números para todas as respostas: a seleção foi dirigida por
falhas/casos de entrevista e abrange versões diferentes. Não equivale a revisar
as dez perguntas n11–n20 integralmente nem substitui as 24 leituras de IA anteriores.
As dez revisões históricas da v1 continuam separadas, sem reclassificação automática.
