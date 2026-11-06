# Rodada final V3: arquivos preservados

Seis arquivos originais copiados byte a byte, hashes em SHA256SUMS. Auditoria
nao encontrou tokens conhecidos. Ambos os resumos foram recalculados e conferem
com os JSONLs. IDs, grupos, snapshots, contextos, prompts renderizados e diagnosticos
foram conferidos contra o protocolo congelado. Zero retries; nenhuma nova inferencia.

## Resultados separados

| Medida | Novas n11-n20 | Antigas q01-q30 (contaminadas) |
| --- | --- | --- |
| Perguntas / chamadas do LLM | 10 / 9 | 30 / 27 |
| Primeiro objeto com schema valido | 9/9 chamadas | 16/27 chamadas |
| Schema valido sem precisar ignorar sufixo | 0/9 chamadas | 0/27 chamadas |
| IDs no contexto, entre respostas com afirmacoes e schema | 7/7 | 10/11 |
| Todos os trechos literais, entre respostas com IDs validos | 4/7 | 9/10 |
| Saidas do LLM aceitas pelo parser | 6/9 | 14/27 |
| Abstencao correta nas negativas, pipeline | 3/3 | 6/6 |
| Chamadas nas negativas | 2 | 4 |
| Abstencao por retrieval vazio, todas as perguntas | 1 | 3 |
| Recusa indevida formal nas respondiveis | 0/7 | 2/24 |
| Fonte relevante no contexto nas respondiveis | 7/7 | 23/24 |
| Erros finais | 3 | 13 |

Nao misturar denominadores: 6/9 aceitas pelo parser incluem duas abstencoes do LLM;
restam quatro respostas substantivas para sete perguntas respondiveis. Somando a
abstencao sem LLM, ha sete resultados operacionais sem erro em dez perguntas.
Isso nao significa sete respostas factualmente corretas.

## Leitura das novas, por Codex/IA

- n11, n13, n17: nucleo factual sustentado. n11 mistura ingles e portugues;
  n13 tem erro de redacao no nome do prato. Nao declarar perfeita aderencia ao idioma.
- n12: aceita pelo parser com ID e trecho reais, mas diz sabor bom usando elogio
  ao custo-beneficio. A mesma review diz gosto ruim. O teste literal nao verifica
  entailment nem distingue aspectos semanticamente.
- n14: bloqueada por velo versus velho. O conteudo principal tem apoio; ha custo
  de falso bloqueio por transcricao estrita. Nao relaxar a regra retrospectivamente.
- n15: atribui Nao valeu a pena a uma review onde nao existe; o trecho esta em outra
  fonte. Ainda usa Nao achei caro para dizer preco alto. O bloqueio evitou entregar
  uma resposta contraditoria, embora a regra detecte existencia, nao polaridade.
- n16: bloqueada por espaco final e mudanca de caixa/transcricao. Tambem combina
  reviews diferentes e responde refrigeracao inadequada quando a pergunta exigia
  adequada no mesmo relato. Falha semantica e falha literal sao distintas.
- n18: abstencao correta sem LLM, por retrieval vazio.
- n19 e n20: abstencoes corretas do modelo no primeiro objeto JSON.

Todos os nove outputs do LLM tinham sufixo: cinco eram apenas ponto final, um tinha
fechamentos adicionais e tres continham explicacao maior. Aceitar o primeiro objeto
funcionou conforme a regra declarada, mas nao significa que o modelo produziu JSON
puro em 100% dos casos. O bruto foi preservado, inclusive o texto ignorado.

Leitura completa das dez em generation-v3-new.review-codex.md/JSON. Origem IA;
confirmacao humana pendente. As metricas originais continuam intactas.

## Registro contaminado: leitura de casos selecionados

Nao foi feita revisao factual completa das 30 aqui. A amostra inspecionada mostra:
q09 agora responde o atraso com evidencia; q01 recebe a fonte da posicao 6 e responde
embalagem, mas acrescenta fechamento/plural sem apoio suficiente nas fontes citadas.
q21 recusa apesar da fonte rotulada relevante. q22 falha por campos extras/text no
lugar de trecho e inclui fonte de elogio entre as criticas. q23 usa a fonte correta
de mensagens ignoradas, mas a frase Os clientes relataram ignorar suas mensagens
fica ambigua/inverte o sujeito. Nao promover 14/27 a acuracia factual.

As antigas foram usadas nas iteracoes e servem apenas de registro de desenvolvimento.
As novas usam corpus conhecido e rotulos de IA: nao sao holdout de documentos nem
gold humano independente. Mudaram prompt, parser, contexto e reserva de tokens juntos;
nao atribuir diferencas a uma unica alteracao. Prompt e parser permanecem congelados.
