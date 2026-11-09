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
anotador. A rodada aguarda execução.
[Rótulos](../data/absa/b2w-human-v1.jsonl) ·
[Manifesto e SHA-256](../data/absa/b2w-human-v1.manifest.json)
