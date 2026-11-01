# Conjunto de referência para aspectos

## Estado e limites

Foram anotadas **100 reviews**, vendo somente `id` e texto, depois de escrever o
[guia de 10 regras](annotation-guide.md). Nenhum rótulo sintético da amostra foi exibido,
consultado ou usado para comparar e ajustar as anotações. O arquivo final foi congelado
com SHA-256 antes de qualquer comparação com o gerador; essa comparação não foi realizada.

**As anotações foram feitas por IA, não por uma pessoa.** Estado registrado:
`ai_annotated_pending_independent_human_review`, com **zero revisões humanas**.
O anotador já conhecia a arquitetura e o design do gerador. O cegamento é aos rótulos
dos registros amostrados, não à existência ou ao vocabulário dos templates. Portanto,
não apresentar esse conjunto como gold humano independente ou como prova final de qualidade.

A anotação consistiu em leitura semântica registro a registro, em blocos de 40, 40 e 20.
O script de seleção não atribui aspectos; a heurística lexical só ajuda a selecionar
candidatos com opiniões mistas. Anotações não foram produzidas por regras de palavras-chave.
Na revisão final de consistência, elogios genéricos ao prato não foram convertidos em
sabor positivo sem evidência específica. Nove registros foram revisados somente pelo guia;
o hash anterior e os IDs afetados estão no manifesto, sem consulta aos rótulos gerados.

## Composição

| Estrato | Quantidade |
|---|---:|
| rest_001, rest_002, rest_003, rest_004 | 13 por restaurante |
| rest_005, rest_006, rest_007, rest_008 | 12 por restaurante |
| Nota 1 | 17 |
| Nota 2 | 17 |
| Nota 3 | 25 |
| Nota 4 | 25 |
| Nota 5 | 16 |
| Reviews com aspectos de polaridades diferentes, segundo a anotação | 52 |
| Reviews com notas sobre ambiguidades ou regras de borda | 25 |

Seleção determinística com seed `1729`, quotas por restaurante/nota e ordenação por hash.
Uma parte de cada estrato prioriza candidatos com pistas lexicais positivas e negativas;
a seleção encontrou 46 candidatos, enquanto a anotação semântica identificou 52 casos mistos.
Essa diferença não é uma métrica de qualidade do gerador ou do extrator.

Foram excluídos **61 IDs previamente inspecionados**, além dos textos equivalentes
normalizados conhecidos. Dentro da amostra não há textos duplicados após casefold e
compactação de espaços. A lista de exposição registra somente IDs e hashes, sem rótulos.

## Arquivos

Todos ficam em `data/gold/`, separados dos dados externos e dos dados brutos:

| Arquivo | Conteúdo |
|---|---|
| `reviews_100.blind.jsonl` | Somente `id` e texto; entrada para anotação cega |
| `aspects_100.ai.jsonl` | `id`, mapa de aspectos anotados e `notas` opcionais |
| `aspects_100.human-template.jsonl` | IDs com `aspects: null`, ainda não anotados por humano |
| `sample_manifest.json` | Seed, estratos, hashes e lista de reserva para treino |
| `annotation_manifest.json` | Autoria por IA, protocolo, estado, hashes e contagens |
| `prior_exposure.json` | IDs e hashes previamente expostos, excluídos da seleção |

`null` no template humano significa **pendente**, nunca ausência de aspectos. Em uma
anotação concluída, ausência de aspectos é `{}`; cada aspecto não mencionado fica sem chave.
Uma revisão humana deve ser salva em outro arquivo, preservando o snapshot por IA.

SHA-256 do arquivo cego:
`311821103d98fa351ee183865964a2aaaf7f9de36c6d927459d2c9830954c75b`

Os hashes dos demais artefatos estão nos manifestos. `.gitattributes` preserva os bytes dos
arquivos congelados e do guia no checkout. O hash do corpus de origem normaliza CRLF/LF,
para não confundir convenção de quebras de linha com alteração do conteúdo.

## Casos de borda aplicados

- Duração isolada sem julgamento de rapidez/prazo não recebe polaridade de entrega.
- Atraso explícito ou espera superior a uma hora recebe tempo_entrega negativo.
- Frio, necessidade de reaquecer ou refrigeração inadequada não provam atraso.
- Demora para responder no chat é atendimento, não tempo_entrega.
- Gosto apenas diferente do habitual não ganha polaridade automaticamente.
- Recomendações e críticas globais não criam aspectos específicos, como preço.
- Caso o mesmo aspecto tenha elogio e crítica explícitos, a regra do formato binário é
  marcar negativo e registrar a mistura em notas; isso não elimina a ambiguidade semântica.

Uma review contém apenas elogio global e recebeu `{}`; não foi inventado aspecto para preencher o mapa.

As decisões foram aplicadas sem consultar as polaridades sintéticas para resolver dúvidas.
Os casos anotados são um ponto de partida para adjudicação humana, não verdades comprovadas.

## Reserva e avaliação

`reserved_from_training_ids` contém **101 IDs**: as 100 reviews e uma duplicata textual
normalizada fora da amostra. Futuras rotinas de treino de ABSA devem excluir esses IDs.
A lista foi preparada; como o treinamento ainda não foi implementado, não há garantia
automática de exclusão em um pipeline futuro que ignore esse contrato.

Essa reserva evita vazamento literal, mas não resolve famílias de templates semelhantes.
O conjunto é interno ao gerador e não demonstra generalização para linguagem real.
Para o benchmark final, use anotação humana independente e controle famílias de templates,
além de avaliar mudança de domínio separadamente. A amostra pública de e-commerce não foi
misturada neste conjunto nem convertida em reviews de restaurante.

## Reprodução e validação

```powershell
python scripts/prepare_gold_sample.py
python scripts/validate_gold_set.py
python -m pytest tests/test_gold_set.py -v
```

O preparador nunca consulta `aspects` e se recusa a substituir uma amostra cega existente
por outra diferente. Os testes usam um mapa que falha se houver acesso a rótulos durante
a seleção. O validador verifica schema, IDs, hashes, estratos, exclusão de exposição prévia,
duplicatas e reserva de treino, sem comparar anotações com os rótulos sintéticos.

Para revisão humana cega: leia primeiro somente o guia e `reviews_100.blind.jsonl`,
preencha uma cópia do template humano e congele o resultado. Consulte a anotação por IA
apenas depois, para comparar e adjudicar divergências, sem sobrescrever silenciosamente
nenhuma das versões. Ainda não foram calculadas métricas do extrator ou concordância humana.
