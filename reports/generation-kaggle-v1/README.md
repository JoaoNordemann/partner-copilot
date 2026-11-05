# Generation Kaggle v1

## Resultado e denominadores

**Prompt `partner-copilot-v1`, contrato estrito: 0/27 saídas do LLM aceitas.**

O JSONL contém 30 tentativas distintas, de q01 a q30, com backend
`real_mistral_nf4`. Houve 27 chamadas ao Mistral; todas terminaram em erro de
validação da saída, preservando o texto bruto. As outras três tentativas
(q13, q29 e q30) retornaram abstenção `retriever_empty`, sem chamar o LLM.
Portanto, o pipeline teve 3/30 resultados formalmente válidos, todos abstenções,
e nenhuma resposta substantiva aceita. Os 27 não são o total de perguntas.

| Falha registrada | Quantidade |
| --- | ---: |
| Marcador de abstenção acompanhado de outro texto | 19 |
| Linha de saída sem citação ao final | 5 |
| Referência de citação inválida para o contexto | 3 |

Esses são os primeiros erros detectados pelo validador; uma saída pode ter
outras violações. As três falhas de citação são q03, q07 e q17. Em q03 e q17,
o texto entre colchetes usa sintaxe adicional ou escapes nos IDs; em q07,
o marcador escapado foi interpretado como referência inválida. Não é correto
concluir que as três saídas inventaram reviews inexistentes apenas pelo código
do erro. Da mesma forma, rejeição pelo contrato não demonstra erro factual.

## Abstenção e limitações

- Nas 6 negativas: 2/6 abstenções válidas, q29 e q30; q25 a q28 tiveram erros.
- Nos quatro negativos q25 a q28: 0/4 abstenções aceitas pelo contrato.
- Nas 24 respondíveis: q13 absteve por retrieval vazio (1/24); as outras 23
  terminaram em erro. A taxa de abstenção indevida isolada não mede utilidade
  quando tantos casos falham no contrato.
- Validade de referências segundo a métrica registrada: 0/27. Essa métrica
  exige ao menos uma citação e todas as referências no contexto, e não mede
  diretamente a fidelidade factual.

A revisão manual permanece pendente no resumo e no arquivo de revisão.
Texto de recusa acompanhado de explicações não conta como abstenção válida
sob o contrato v1. Não reinterpretar esses erros como alucinações factuais
sem ler e comparar as afirmações com o contexto.

## Proveniência e preservação

Execução reportada em Tesla T4, Python 3.13.16, Torch 2.11.0+cu130,
Mistral em NF4 e código do commit
`5ebe981c36db75f28ddc2e94e319de95e2a77cbf`.
Versões completas, configuração, prompt, contexto, saída bruta, latência e VRAM
estão nos artefatos. O ambiente separado coincide com o de todas as linhas.
O resumo foi recalculado e conferido com o JSONL durante a preservação.
A auditoria automatizada não encontrou tokens conhecidos ou credenciais nos
arquivos recebidos.

Os arquivos recebidos foram preservados byte a byte, incluindo erros,
smoke test e o lock vazio (artefato operacional, sem resultados).
`SHA256SUMS` registra os hashes desses arquivos originais. Este README é uma
análise adicional; não altera nem substitui os resultados. Qualquer rodada
com novo prompt deve usar outro nome e outro diretório.
