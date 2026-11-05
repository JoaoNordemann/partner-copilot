# Verificacao JSON v1: resultados recebidos

Tres artefatos preservados byte a byte; hashes em SHA256SUMS. Sem tokens conhecidos
na auditoria automatizada. Dez IDs unicos e ordenados, um experimento, perguntas e
contextos conferidos com o snapshot congelado. Resumo recalculado sem divergencias.

| Medida automatica | Resultado |
| --- | --- |
| Chamadas do LLM | 10 |
| Schema valido / aceita pelo parser | 7/10 |
| IDs no contexto, entre respostas com schema e afirmacoes | 7/7 |
| Evidencia no contexto nas respondiveis | 7/7 |
| Abstencao correta nas negativas | 0/3 |
| Recusa indevida nas respondiveis | 0/7 |
| Abstencao por retrieval vazio | 0 |
| Correcoes / retries | 0 |

O 0/7 de recusa indevida nao significa sete respostas uteis: duas respondiveis
falharam no esquema. Schema valido tambem nao implica resposta correta.

As tres rejeicoes (n02, n03, n08) sao texto adicional apos um objeto JSON completo,
nao ausencia de chaves ou estouro do limite de tokens. Inspecionar o prefixo foi
apenas diagnostico; nenhuma saida foi reparada ou recontada como aceita.

n09 passou no JSON e na verificacao de ID, mas inventou que houve analise
microbiologica de Yakisoba. A fonte citada so fala de comida e atraso. n10 reconhece
que nao ha CNPJ no contexto, mas declara abstem=false: falha de abstencao detectavel
por maquina. n08 responde entrega em vez de lote e contradiz informacoes de sabor
e temperatura do contexto. Esses casos impedem tratar formato como fidelidade.

Leitura das dez respostas por Codex/IA em generation-json-v1.review-codex.md e JSON
correspondente. Confirmacao humana pendente. O checklist e o resumo exportados
permanecem preservados com seus estados originais.

GPU Tesla T4. Geracao somada: aproximadamente 72,9 s; mediana por chamada: 6,18 s.
Carga unica do modelo: aproximadamente 99,5 s. O campo de carga reaparece em cada
linha de metricas, mas nao deve ser somado dez vezes. Nenhuma saida atingiu o limite
de tokens. Tempos nao incluem necessariamente download ou indexacao.

Nao comparar diretamente 7/10 com 2/27 como ganho causal: o conjunto mudou e esta
checagem tem fontes relevantes no contexto em todas as sete respondiveis. Sao
perguntas novas em corpus conhecido, nao holdout independente de documentos.
Prompt e parser permanecem congelados; nenhuma nova inferencia ou iteracao foi
realizada durante esta analise.
