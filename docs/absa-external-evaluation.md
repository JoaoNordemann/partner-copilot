# Avaliação externa do extrator ABSA

A B2W-Reviews01 contém reviews reais de comércio eletrônico em português do
Brasil. A [fonte original](https://github.com/americanas-tech/b2w-reviews01/blob/4639429ec698d7821fc99a0bc665fa213d9fcd5a/README.md#licensing)
declara CC BY-NC-SA 4.0. A [preparação local](external-data.md) registra
atribuição, revisão, transformações e hashes da amostra de 200 reviews.
O diagnóstico mede transferência para texto real de comércio eletrônico.

## Anotação e congelamento

O lote cego tem 30 reviews, seis por nota. Dentro de cada nota, selecionar
os seis menores hashes SHA-256 de `absa-external-v1`, um separador NUL e o
ID externo. Ordenar o lote inteiro pelo mesmo hash. O anotador recebe
apenas os IDs e os textos e anota em uma única sessão, antes de rodar o
modelo ou consultar saídas do TF-IDF. Registrar casos difíceis com
`ambíguo` em notas e omitir o par em dúvida. Um mapa vazio é válido.

Aplicar o [guia congelado](annotation-guide.md) com o seguinte mapeamento
de domínio, fixado antes de ler o lote.

| Aspecto | Evidência que entra |
| --- | --- |
| Tempo de entrega | Prazo ou rapidez, incluindo atraso e prazo cumprido. Produto quebrado ou não recebido sem evidência temporal não recebe esse par. |
| Embalagem | Opinião explícita sobre acondicionamento, lacre, recipiente ou proteção. Produto quebrado entra aqui só se a review relacionar o dano à embalagem. |
| Preço | Opinião explícita sobre preço ou custo-benefício. |
| Atendimento | Resposta, contato, educação ou resolução da reclamação, com opinião identificável. |

Defeito ou qualidade do produto fica fora dos quatro aspectos. Sabor e
temperatura entram apenas na auditoria das previsões, com contagem por
aspecto e número de reviews que receberam ao menos um desses rótulos.

Antes de rodar, conferir os 30 IDs, unicidade e esquema, calcular SHA-256
do JSONL de rótulos e fazer commit do arquivo com IDs e rótulos e de seu
manifesto. Preservar localmente textos, notas livres que citem texto e
previsões brutas. O repositório publica a referência da fonte e o
[script de download](../scripts/prepare_external_reviews.py). Os termos
da [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.pt-br)
exigem atribuição, uso não comercial e licença compatível na distribuição
de adaptações. O lote segue o uso de avaliação não comercial.

## Medição e interpretação

Com o checkpoint 253 e a geração congelada, medir validade JSON nos 200
textos. Nos 30 anotados, reportar acerto exato, TP, FP e FN para os quatro
aspectos, incluindo quantas reviews com rótulo vazio receberam ao menos
um par indevido. Mostrar suporte por par e omitir F1 individual com
suporte abaixo de 10. Reportar macro-F1 descritivo dos pares com suporte,
com o número de pares incluídos. Uma saída inválida perde todos os pares
esperados. Avaliar o TF-IDF nos mesmos 30 IDs com ajuste apenas no treino
sintético.

Antes da execução, considerar sinais de problema para uso externo:
mais de 10/200 JSONs inválidos (5%), mais de 30% dos pares anotados
omitidos (FN dividido por TP + FN), ou mais de 20% das reviews de
referência vazia com ao menos um dos quatro pares indevidos. Mostrar os
denominadores. Quando um denominador for zero, declarar a taxa indisponível.
Esses limites são critérios diagnósticos, sem ajuste após ver resultados.

O autor lê ao menos dez previsões, incluindo todos os casos com falso
positivo. Se houver mais de dez, lê todos esses casos. Completa o mínimo
de dez pela ordem fixa do lote. Se houver tempo, o mesmo anotador reanota
os dez primeiros textos no dia seguinte, sem ver os rótulos anteriores
nem as previsões. Registrar concordância exata por review e divergências
por par, preservando os rótulos originais como referência principal.

A amostra de 200 está verificada. A referência humana v1 tem 30 IDs,
19 mapas vazios e 12 pares anotados após dois ajustes confirmados pelo
anotador. A rodada foi executada uma vez no Kaggle em uma Tesla T4.
[Rótulos](../data/absa/b2w-human-v1.jsonl) ·
[Manifesto e SHA-256](../data/absa/b2w-human-v1.manifest.json)

## Resultado do checkpoint 253

O QLoRA produziu 172/200 JSONs válidos (86,0%). Das 28 saídas inválidas,
27 falharam na validação de aspecto ou polaridade e uma na sintaxe JSON.
Entre os 200 textos, 87 receberam ao menos um rótulo válido de sabor ou
temperatura, com 74 menções a sabor e 25 a temperatura.

| Métrica nos 30 textos anotados | QLoRA | TF-IDF + regressão logística |
| --- | ---: | ---: |
| Conjunto exato | 9/30 | 18/30 |
| JSON inválido | 8/30 | 0/30 |
| Pares corretos | 9 | 5 |
| Pares extras | 20 | 8 |
| Pares omitidos | 3 | 7 |
| Referências vazias com par extra | 10/19 | 5/19 |
| Macro-F1 descritivo, cinco pares com suporte | 0,6758 | 0,2171 |

| Par | Suporte | QLoRA TP / FP / FN | TF-IDF TP / FP / FN |
| --- | ---: | ---: | ---: |
| Entrega positiva | 4 | 3 / 4 / 1 | 4 / 2 / 0 |
| Entrega negativa | 2 | 2 / 2 / 0 | 0 / 2 / 2 |
| Embalagem positiva | 0 | 0 / 2 / 0 | 0 / 0 / 0 |
| Embalagem negativa | 0 | 0 / 7 / 0 | 0 / 0 / 0 |
| Preço positivo | 3 | 1 / 0 / 2 | 1 / 3 / 2 |
| Preço negativo | 0 | 0 / 4 / 0 | 0 / 0 / 0 |
| Atendimento positivo | 1 | 1 / 1 / 0 | 0 / 1 / 1 |
| Atendimento negativo | 2 | 2 / 0 / 0 | 0 / 0 / 2 |

O QLoRA excedeu dois limites predefinidos. A taxa de JSON inválido foi
14,0% e a de referências vazias com par extra foi 52,6%. A taxa de omissão
ficou em 25,0%, abaixo do limite de 30%. O modelo recuperou mais pares
anotados que o TF-IDF e também acrescentou mais pares sem suporte. Os
pares sem suporte ficam fora do macro-F1 e seus falsos positivos entram
nas contagens e no acerto exato. A avaliação descreve a transferência
de entrega de comida sintética para comércio eletrônico real.

O ZIP bruto permanece local. Seu SHA-256 é
`3cc01d66290bfe6da9066b58f80d2a85ae7180b0025f6a039163d55e5095927d`.


## Baselines complementares e transferência

A expectativa da avaliação era uma queda em relação ao sintético, em
especial para o TF-IDF treinado nesse domínio. Os limites de validade,
omissão e falsos positivos em referências vazias foram registrados no
commit `8cf0cc2`, antes da inferência. O baseline de regras foi calculado
depois da primeira rodada, com as mesmas expressões do avaliador
sintético, que já estavam versionadas antes da B2W.

As regras acertaram o conjunto de pares em **23/30 reviews**, com **6
pares corretos, 2 extras e 6 omitidos**. As 30 saídas passaram no parser.
Houve par extra em **2/19** referências vazias. O macro-F1 descritivo foi
**0,4100**. Os dois falsos positivos foram de prazo. Em
`b2w_row_131837`, a rapidez descreve o produto. Em `b2w_row_018390`,
o texto pergunta quanto tempo levou a entrega. Os mesmos textos já
faziam parte da revisão humana de QLoRA e TF-IDF.

| Par | Suporte | Regras TP / FP / FN |
| --- | ---: | ---: |
| Entrega positiva | 4 | 3 / 1 / 1 |
| Entrega negativa | 2 | 1 / 1 / 1 |
| Embalagem positiva | 0 | 0 / 0 / 0 |
| Embalagem negativa | 0 | 0 / 0 / 0 |
| Preço positivo | 3 | 2 / 0 / 1 |
| Preço negativo | 0 | 0 / 0 / 0 |
| Atendimento positivo | 1 | 0 / 0 / 1 |
| Atendimento negativo | 2 | 0 / 0 / 2 |

A validade do QLoRA caiu de **100/100 no gold sintético para 172/200
na B2W**, uma diferença de 14 pontos percentuais. Para comparar
macro-F1, recalculamos o gold sintético sobre os mesmos cinco pares
com suporte na B2W. O QLoRA passou de **0,9830 para 0,6758** e o TF-IDF
de **0,8817 para 0,2171**. A diferença é descritiva. Os conjuntos
têm domínios, suportes por par e tamanhos diferentes.
[Métricas do gold sintético](../reports/absa-eval-checkpoint-253-v1/final.json)

A sessão complementar usou as quatro demonstrações congeladas do treino
e os mesmos 30 IDs para avaliar o Qwen base, com o adapter desativado.
O Qwen acertou **0/30 conjuntos exatos**. Produziu **28/30 saídas válidas**,
com **12 pares corretos, 95 extras e zero omissões**. Houve ao menos um
par extra em **17/19** referências vazias. O macro-F1 descritivo nos
cinco pares com suporte foi **0,3996**. Todos os 28 JSONs válidos
trouxeram algum par extra. Os outros dois foram rejeitados por aspecto
ou polaridade fora do contrato. A revisão dos casos do few-shot foi
preparada para o anotador.

| Par | Suporte | Qwen few-shot TP / FP / FN |
| --- | ---: | ---: |
| Entrega positiva | 4 | 4 / 2 / 0 |
| Entrega negativa | 2 | 2 / 19 / 0 |
| Embalagem positiva | 0 | 0 / 8 / 0 |
| Embalagem negativa | 0 | 0 / 18 / 0 |
| Preço positivo | 3 | 3 / 4 / 0 |
| Preço negativo | 0 | 0 / 19 / 0 |
| Atendimento positivo | 1 | 1 / 6 / 0 |
| Atendimento negativo | 2 | 2 / 19 / 0 |

Na mesma sessão em Tesla T4, medimos o checkpoint 253 em 30 outros
textos da amostra, com lote unitário e cinco aquecimentos excluídos
das estatísticas. Com o modelo já carregado, a latência de tokenização,
inferência e decodificação foi **1,41 s de mediana**, **2,38 s de p95**
e **3,07 s de máximo**. O pico de VRAM foi **1,17 GiB alocada** e
**1,88 GiB reservada**. A medição exclui leitura de arquivos, carga
do modelo e rede.

O ZIP complementar permanece local. Seu SHA-256 é
`bfca2d10264e66916ff63a968bcb4c16c48944b6227774811ed4670ed5af9dde`.

## Conclusão

> O extrator, treinado só com dados sintéticos de restaurantes, acertou o conjunto completo de aspectos e polaridades em 9 de 30 textos reais de e-commerce anotados por mim (30%), contra 23 de 30 (76,7%) do melhor baseline nesse critério, as regras por palavras-chave. Amostra pequena, um único anotador, domínio diferente.
>
> O treino ensinou o extrator a reproduzir as convenções do gerador, mas a queda em texto real e os falsos positivos indicam que ele ainda depende de pistas lexicais e falha ao ligar palavras como “rápido” ao que elas descrevem, ou ao deixar um aspecto sem rótulo quando falta evidência.

## Revisão humana das previsões

O anotador revisou os 17 IDs com ao menos um falso positivo pontuado em
qualquer dos métodos. São 13 IDs no QLoRA e sete no TF-IDF, com três em
comum. A revisão interpreta as previsões em relação à referência já
congelada. No caso 02, a observação sobre embalagem confirma a omissão
que já constava na referência v1.

| Julgamento dos pares extras pontuados | QLoRA | TF-IDF |
| --- | ---: | ---: |
| Sem evidência textual | 16 | 6 |
| Ambíguo | 4 | 1 |
| Contradito pelo texto | 0 | 1 |
| Total | 20 | 8 |

No QLoRA, os quatro pares ambíguos foram três de embalagem e um de
preço. No TF-IDF, a contradição foi atendimento positivo diante de
uma reclamação de atendimento. O anotador também revisou duas saídas
brutas do QLoRA rejeitadas pelo parser. Os aspectos fora do contrato
dessas duas saídas ficaram no diagnóstico qualitativo. As previsões
válidas de sabor e temperatura foram examinadas como confusão de domínio,
fora da contagem de pares extras dos quatro aspectos.

| ID | QLoRA | TF-IDF |
| --- | --- | --- |
| b2w_row_029847 | Sabor sem evidência. | Sabor sem evidência. Atendimento positivo contradiz a reclamação. |
| b2w_row_033377 | Embalagem e preço ambíguos. O dano não é atribuído à embalagem e a menção ao valor é contextual. | Sabor sem evidência. |
| b2w_row_055345 | Prazo, embalagem e preço sem evidência. A crítica aborda falha do produto e atendimento. | Sabor e temperatura sem evidência. |
| b2w_row_123422 | Sabor fora do recorte. Embalagem ambígua, pois o defeito parece estar no frasco do produto. | Sabor e prazo sem evidência. |
| b2w_row_000449 | Atendimento sem evidência. O verbo se refere à utilidade do produto. | Saída vazia. |
| b2w_row_125467 | Sabor e prazo sem evidência. A duração mencionada se refere ao uso. | Saída vazia. |
| b2w_row_047123 | Sabor e embalagem sem evidência. | Temperatura sem evidência. |
| b2w_row_038164 | Sabor, prazo e embalagem sem evidência. A rapidez descreve o produto. | Sabor e prazo sem evidência. |
| b2w_row_131837 | Sabor, prazo e preço sem evidência. Embalagem ambígua diante de um defeito do produto. | Sabor sem evidência. |
| b2w_row_103622 | Embalagem e preço sem evidência. O texto critica a dimensão do produto. | Saída vazia. |
| b2w_row_018390 | Prazo positivo sem evidência. O texto é uma pergunta. | Sabor e prazo negativo sem evidência. |
| b2w_row_124379 | Prazo negativo sem evidência de atraso. | Sabor e temperatura sem evidência. |
| b2w_row_060054 | Sabor e embalagem sem evidência. A crítica é ao tamanho e à fixação do produto. | Sabor sem evidência. |
| b2w_row_117689 | Sabor e embalagem sem evidência. A crítica é à apresentação do conteúdo. | Sabor sem evidência. |
| b2w_row_109399 | Saída rejeitada por chaves de componentes e garantia. Preço positivo ambíguo na saída bruta. | Sabor e prazo sem evidência. Preço positivo ambíguo. |
| b2w_row_008617 | Coincide com a referência. | Preço positivo sem evidência. A recomendação é genérica. |
| b2w_row_074082 | Saída rejeitada por chaves de funcionalidade e requisito de internet. | Preço positivo sem evidência. O texto descreve um requisito de internet. |

A segunda anotação cega opcional ainda não foi realizada.
