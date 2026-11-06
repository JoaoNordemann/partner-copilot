# Experimento D: resultados preservados

Os tres arquivos recebidos foram copiados byte a byte. SHA256SUMS registra os
hashes originais. Analise derivada: Codex / IA. Revisao humana de D: pendente.

## Integridade

- 30 perguntas unicas e ordenadas; 90 eventos no ledger.
- Uma unica identidade de experimento.
- Primeiras respostas e contextos iguais ao B recebido, conferidos por ID e hash.
- 25 correcoes solicitadas, todas com saida salva; nenhuma terceira tentativa.
- Resumo diagnostico recalculado e consistente com o arquivo recebido.
- Auditoria automatizada nao encontrou tokens conhecidos nos tres anexos.

## Comparacao isolada

| Medida | C: parser v2 sobre B | D: uma correcao |
| --- | --- | --- |
| Saidas do LLM aceitas pelo contrato | 2/27 | 2/27 |
| Saidas rejeitadas | 25/27 | 25/27 |
| Novas chamadas ao modelo | 0 | 25 |
| Ganho de aceitacao | referencia | 0 |

As 25 correcoes continuaram rejeitadas. As duas aceitas, q05 e q23, foram herdadas
do baseline C e nao receberam correcao. q13, q29 e q30 abstiveram sem chamada ao
modelo e nao entram no denominador 27. Existem 5/30 resultados sem erro de contrato,
mas tres sao abstencoes sem LLM. Isso nao equivale a cinco respostas corretas.

Nas seis negativas: abstencao estrita 2/6 e tolerante 2/6. Nas quatro negativas
com LLM (q25-q28): 0/4 nas duas metricas. Isso vale tambem na visao normalizada.
Recusa em linguagem livre pode estar presente sem ser reconhecida pelo marcador.

## Conteudo das duas respostas aceitas

- q05: responde a falhas de acondicionamento com a tampa solta; a fonte rev_001123
  efetivamente relata tampa solta. Passa no formato e tem apoio no trecho.
- q23: pergunta por conversa com a loja sem retorno, mas responde sobre embalagem
  solta em rev_001123. A fonte existe e o formato passa; a resposta nao atende a
  pergunta. O contexto continha rev_001265: O restaurante ignorou minhas mensagens.

Portanto, 2/27 e aceitacao pelo parser, nao acuracia. Apenas esses dois casos
aceitos foram inspecionados aqui quanto a relevancia da resposta; nao extrapolar
uma taxa factual sobre todas as saidas.

## Falhas e custo

O campo error.code do runner D agrupa inclusive InvalidCitationError como
generation_contract_error. Para separar causas, usar error.type e error.message;
nao afirmar que desapareceram erros de citacao apenas porque mudou o codigo.
O detalhamento e salvo em analysis.json.

As 25 correcoes somaram aproximadamente 290 segundos de geracao e 406 segundos
medidos ao redor das chamadas, incluindo carga quando necessaria. Esses valores
nao incluem a execucao historica de B e nao sao benchmark de execucao continua.
As metricas individuais de tokens, tempo e VRAM permanecem nas duas tentativas.

Esta rodada nao trouxe ganho de aceitacao sobre C. Preservar o resultado negativo,
sem repetir correcoes ou relaxar o contrato retroativamente. Eventuais novas
hipoteses exigem outra versao e outro experimento. Todos os ajustes foram feitos
apos observar resultados nas mesmas 30 perguntas; nao e avaliacao independente.


## Classificacao posterior e estrategia

Retry descartado da pipeline; permanece somente como experimento historico.
A tabela de tokens rejeitados e a separacao entre aceita pelo parser e sustentada
para a pergunta estao em [analise da transicao](../../docs/generation-output-analysis.md).
A classificacao detalhada tambem esta em citation-classification.json.


## Categorias primarias das 14 citacoes invalidas

| Categoria | Casos |
| --- | ---: |
| Varios IDs existentes no mesmo colchete | 6 |
| IDs alterados (prefixo ou zeros) | 2 |
| Marcador interpretado como citacao | 4 |
| Tags de bloco / texto entre colchetes | 2 |
| ID existente fora dos cinco documentos enviados | 0 |

A classificacao primaria e exclusiva; problemas secundarios podem coexistir.
Os tokens exatos estao em citation-classification.json. Underscores escapados
ja estavam normalizados pelo parser-v2, portanto nao sao a causa residual sozinhos.

| Caso | Aceita pelo parser | Sustentada e pertinente para a pergunta (leitura por IA) |
| --- | --- | --- |
| q05 | sim | sim |
| q23 | sim | nao: pergunta de mensagens ignoradas, resposta de embalagem |
| 25 rejeitadas | nao | revisao completa de conteudo pendente |
