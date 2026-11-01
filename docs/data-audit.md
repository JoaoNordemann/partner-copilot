# Auditoria do dataset sintético

Referência: 3.000 reviews, seed 42, data final 2026-11-01 e histórico de 90 dias.

Foram lidas 50 reviews antes de alterar o gerador e outras 50 após a revisão. A seleção inclui as primeiras seis de cada restaurante e uma adicional de rest_002 e rest_004. É uma inspeção qualitativa distribuída pelos oito restaurantes, não uma amostra aleatória.

## Diagnóstico e correções

- O corpus anterior era claramente baseado em templates. Exemplos: rev_000003 exigia esquentar açaí no micro-ondas; rev_000005 descrevia açaí como salgado; rev_000066 tratava combo de sushi gelado como problema. Doces também recebiam frases de comida quente e salgada.
- A seleção de linguagem agora respeita temperatura esperada por item: sushi frio não recebe o mesmo tratamento que hot roll; sobremesas refrigeradas e produtos de temperatura ambiente também são diferenciados. Frases de sabor foram reformuladas para não impor tempero salgado a doces.
- Mais variantes por aspecto, abertura e conclusão opcionais em 20% das reviews cada, e conclusões diferentes para avaliações mistas. Isso reduz o domínio das mesmas frases.
- Reviews com aspecto negativo não recebem nota 5; reviews somente negativas não recebem nota maior que 3. A fórmula geral de notas foi preservada, com esses limites de consistência.
- Os fluxos pseudoaleatórios de população e linguagem foram separados. Mudanças futuras em frases não alteram automaticamente os restaurantes, datas, aspectos e notas amostrados.
- O acréscimo de negatividade de sabor em rest_007 passou de 0,05 para 0,15. Na primeira recontagem revisada, o efeito de 0,05 desapareceu na variabilidade amostral (18,1% versus 18,6% no controle). Não foram alteradas as probabilidades de atraso temporal.

## Repetição literal

Segmentação por espaço após ponto, exclamação ou interrogação; preserva caixa, acentos e pontuação. Dois fragmentos são iguais somente se seus textos forem literalmente iguais após remover espaços externos. Fragmentos após dois-pontos não são separados. Ruído ortográfico pode ocultar repetições semânticas.

| Métrica | Antes | Depois |
|---|---:|---:|
| Ocorrências de frases | 10642 | 8107 |
| Frases distintas | 1267 | 2314 |
| Frases distintas que aparecem mais de uma vez | 668 | 1231 |
| Repetições além da primeira ocorrência | 9375 | 5793 |
| Reviews completas duplicadas além da primeira ocorrência | 58 | 105 |

Antes: repetições excedentes / ocorrências = 88.1%.

| Frase mais repetida | Ocorrências |
|---|---:|
| Pedi pro jantar. | 462 |
| Primeira vez pedindo aqui. | 381 |
| Recomendo! | 378 |
| Nota 10. | 375 |
| Já virou meu pedido fixo. | 336 |

Depois: repetições excedentes / ocorrências = 71.5%.

| Frase mais repetida | Ocorrências |
|---|---:|
| Entregaram dentro do prazo. | 129 |
| Chegou no horário que o app mostrou. | 92 |
| A embalagem veio bem fechada. | 77 |
| Pedi pra dividir aqui em casa. | 73 |
| Foi minha primeira compra aqui. | 70 |

O número de frases distintas repetidas cresceu porque há mais variantes distintas. A proporção excedente caiu; isso não significa que o corpus deixou de ser templated. Reviews completas duplicadas aumentaram com a maior frequência de textos curtos. Não foram adicionados identificadores ou ruído só para fabricar unicidade.

## Distribuição de notas

| Nota | Antes | Depois | Depois (%) |
|---|---:|---:|---:|
| 1 | 188 | 171 | 5.7% |
| 2 | 340 | 340 | 11.3% |
| 3 | 675 | 662 | 22.1% |
| 4 | 886 | 934 | 31.1% |
| 5 | 911 | 893 | 29.8% |

Média: 3.664 → 3.679. Nota 5 com aspecto negativo: 2 → 0.

A distribuição tem preferência por notas altas, com massa relevante em 1, 2 e 3. É plausível como cenário sintético, mas não foi calibrada com dados reais do iFood.

## Pontos fracos no corpus revisado

Taxas condicionais às reviews que mencionam o aspecto. O controle agrupa restaurantes sem ponto fraco configurado naquele aspecto. Para tempo_entrega, ambas as populações usam somente datas anteriores a 2026-10-19, isolando a tendência recente.

| Restaurante | Aspecto | Negativas / menções | Controle sem esse ponto fraco |
|---|---|---:|---:|
| rest_001 | temperatura | 72/148 (48.6%) | 110/682 (16.1%) |
| rest_001 | embalagem | 45/144 (31.2%) | 88/474 (18.6%) |
| rest_002 | embalagem | 53/122 (43.4%) | 88/474 (18.6%) |
| rest_003 | sabor | 83/274 (30.3%) | 297/1593 (18.6%) |
| rest_003 | tempo_entrega | 75/182 (41.2%) | 195/1065 (18.3%) |
| rest_004 | temperatura | 51/128 (39.8%) | 110/682 (16.1%) |
| rest_005 | embalagem | 66/126 (52.4%) | 88/474 (18.6%) |
| rest_005 | temperatura | 57/128 (44.5%) | 110/682 (16.1%) |
| rest_006 | tempo_entrega | 61/194 (31.4%) | 195/1065 (18.3%) |
| rest_007 | preco | 42/78 (53.8%) | 84/508 (16.5%) |
| rest_007 | sabor | 81/271 (29.9%) | 297/1593 (18.6%) |
| rest_008 | embalagem | 57/138 (41.3%) | 88/474 (18.6%) |

Todos os 12 pontos fracos configurados estão acima do respectivo controle nesta referência. São comparações descritivas de dados simulados, não inferência causal sobre restaurantes reais.

## Atrasos por semana

Contagem = reviews com tempo_entrega negativo / reviews que mencionam tempo_entrega. Uma review sem menção de entrega não é contada como entrega pontual. Os intervalos são semanas de sete dias alinhadas à data final; nesta referência coincidem com segunda-feira a domingo.

| Período | rest_002 antes | rest_002 depois | rest_004 antes | rest_004 depois |
|---|---:|---:|---:|---:|
| 2026-09-21 a 2026-09-27 | 2/19 (10.5%) | 6/16 (37.5%) | 3/11 (27.3%) | 2/22 (9.1%) |
| 2026-09-28 a 2026-10-04 | 2/11 (18.2%) | 3/10 (30.0%) | 2/12 (16.7%) | 5/20 (25.0%) |
| 2026-10-05 a 2026-10-11 | 1/20 (5.0%) | 4/12 (33.3%) | 4/18 (22.2%) | 2/12 (16.7%) |
| 2026-10-12 a 2026-10-18 | 2/18 (11.1%) | 3/19 (15.8%) | 3/17 (17.6%) | 2/18 (11.1%) |
| 2026-10-19 a 2026-10-25 | 11/18 (61.1%) | 10/15 (66.7%) | 17/24 (70.8%) | 10/16 (62.5%) |
| 2026-10-26 a 2026-11-01 | 13/15 (86.7%) | 13/15 (86.7%) | 19/21 (90.5%) | 14/20 (70.0%) |

rest_002: histórico anterior aos 14 dias = 44/167 (26.3%); últimos 14 dias = 23/30 (76.7%).

rest_004: histórico anterior aos 14 dias = 26/175 (14.9%); últimos 14 dias = 24/36 (66.7%).

A tendência aparece nas duas últimas semanas nos dois restaurantes. Os denominadores semanais são pequenos, portanto os percentuais semanais têm variabilidade.

## Validação e limites

- 55 testes passaram; lint e formatação aprovados.
- Nova geração com os mesmos parâmetros produziu os dois arquivos idênticos byte a byte.
- O corpus continua sintético, com vocabulário finito, aspectos independentes e polaridades binárias. Não representa a diversidade completa de reviews reais.
- Serve para desenvolver e verificar o RAG e como bootstrap de ABSA. Não deve ser a única base para alegar qualidade de um modelo treinado.
- Antes de separar treino e avaliação, agrupar duplicatas normalizadas e famílias de templates. O gold set deve ter redação independente e anotação humana; sortear templates irmãos para ambos os conjuntos pode inflar artificialmente o resultado.
- Regenerar textos preservando IDs torna índices existentes desatualizados; execute a ingestão novamente caso já tenha indexado o corpus anterior.

## Como reproduzir

```powershell
python scripts/generate_synthetic_data.py --n 3000 --seed 42 --end-date 2026-11-01 --days 90 --validate
python scripts/audit_synthetic_data.py --end-date 2026-11-01 --output work/data-audit/current.json
python -m pytest
```

## 50 exemplos anteriores à revisão

### rev_000008 — rest_001 — nota 3 — 2026-10-03

Veio frio e murcho, decepção. Atendimento atencioso, resolveram rápido. Dá pra melhorar.

Aspectos: {"temperatura": "neg", "atendimento": "pos"}

### rev_000010 — rest_001 — nota 5 — 2026-10-11

O sabor de Pizza Portuguesa surpreendeu, muito bem feito. Embalagem bem vedada, nada vazou. Recomendo

Aspectos: {"sabor": "pos", "embalagem": "pos"}

### rev_000025 — rest_001 — nota 1 — 2026-10-29

Primeira vez pedindo aqui. Esperei mais de uma hora pelo pedido, atraso absurdo. Pizza Calabresa veio sem tempero, bem sem graça. Não recomendo.

Aspectos: {"sabor": "neg", "tempo_entrega": "neg"}

### rev_000029 — rest_001 — nota 4 — 2026-10-21

Pedi pro jantar. Pizza Quatro Queijos tem gosto de comida caseira, caprichado. Chegou em 25 minutos, bem antes do previsto. Já virou meu pedido fixo.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos"}

### rev_000036 — rest_001 — nota 4 — 2026-09-04

Pedido de Pizza Margherita: Qualidade excelente em Pizza Margherita, ingredientes frescos. Recomendo!

Aspectos: {"sabor": "pos"}

### rev_000039 — rest_001 — nota 4 — 2026-09-26

Pedi pro jantar. Chegou em 28 minutos, bem antes do previsto. Já virou meu pedido fixo.

Aspectos: {"tempo_entrega": "pos"}

### rev_000001 — rest_002 — nota 1 — 2026-10-29

Pedi pro jantar. Ingredientes de Burger Duplo pareciam velhos, gosto ruim. A entrega atrasou 107 min e ninguém avisou nada. Caro pelo que entrega, porção pequena.

Aspectos: {"sabor": "neg", "tempo_entrega": "neg", "preco": "neg"}

### rev_000013 — rest_002 — nota 3 — 2026-10-15

Bebida gelada e comida quente, tudo certo. Burger Duplo muito salgado, difícil de comer. Dá pra melhorar.

Aspectos: {"sabor": "neg", "temperatura": "pos"}

### rev_000021 — rest_002 — nota 4 — 2026-09-08

Pedi X-Salada. Qualidade excelente em X-Salada, ingredientes frescos. Bebida gelada e comida quente, tudo certo. Prazo estourou, chegou quase 100 minutos depois do combinado. Já virou meu pedido fixo.

Aspectos: {"sabor": "pos", "tempo_entrega": "neg", "temperatura": "pos"}

### rev_000032 — rest_002 — nota 5 — 2026-10-24

Pedido de Batata Frita Grande: Ótimo custo-benefício, porção generosa. Qualidade excelente em Batata Frita Grande, ingredientes frescos. Bebida gelada e comida quente, tudo certo. Nota 10

Aspectos: {"sabor": "pos", "temperatura": "pos", "preco": "pos"}

### rev_000033 — rest_002 — nota 3 — 2026-10-06

pedi x-salada. pontual, chegou no horário combinado. restaurante muito educado no contato. bebida gelada e comida quente, tudo certo. o sabor de x-salada estava estranho, parecia requentado. ok, nada demais.

Aspectos: {"sabor": "neg", "tempo_entrega": "pos", "temperatura": "pos", "atendimento": "pos"}

### rev_000042 — rest_002 — nota 4 — 2026-10-02

Embalagem bem vedada, nada vazou. Nota 10.

Aspectos: {"embalagem": "pos"}

### rev_000019 — rest_003 — nota 3 — 2026-08-15

Demorou 112 minutos, muito além do prazo informado. Hot Roll tem gosto de comida caseira, caprichado. Ok, nada demais.

Aspectos: {"sabor": "pos", "tempo_entrega": "neg"}

### rev_000030 — rest_003 — nota 5 — 2026-10-08

Pedi Temaki Salmão. Chegou em 27 minutos, bem antes do previsto. Já virou meu pedido fixo.

Aspectos: {"tempo_entrega": "pos"}

### rev_000031 — rest_003 — nota 4 — 2026-09-27

Muito bem embalado, chegou intacto. Recomendo!

Aspectos: {"embalagem": "pos"}

### rev_000066 — rest_003 — nota 3 — 2026-09-07

muito bem embalado, chegou intacto. pontual, chegou no horário combinado. combo 20 peças chegou gelado, claramente ficou parado esperando. ok, nada demais.

Aspectos: {"tempo_entrega": "pos", "temperatura": "neg", "embalagem": "pos"}

### rev_000073 — rest_003 — nota 3 — 2026-08-26

Hot Roll tem gosto de comida caseira, caprichado. Prazo estourou, chegou quase 114 minutos depois do combinado. Da pra melhorar

Aspectos: {"sabor": "pos", "tempo_entrega": "neg"}

### rev_000074 — rest_003 — nota 5 — 2026-09-06

Pedi pro jantar. Pontual, chegou no horário combinado. Já virou meu pedido fixo.

Aspectos: {"tempo_entrega": "pos"}

### rev_000015 — rest_004 — nota 5 — 2026-08-08

Qualidade excelente em Marmita Executiva, ingredientes frescos. Já virou meu pedido fixo.

Aspectos: {"sabor": "pos"}

### rev_000018 — rest_004 — nota 5 — 2026-09-16

Qualidade excelente em Strogonoff, ingredientes frescos. Pontual, chegou no horário combinado. Já virou meu pedido fixo.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos"}

### rev_000020 — rest_004 — nota 4 — 2026-10-14

Pedido de Marmita Executiva: Qualidade excelente em Marmita Executiva, ingredientes frescos. Ja virou meu pedido fixo.

Aspectos: {"sabor": "pos"}

### rev_000050 — rest_004 — nota 5 — 2026-10-24

Pedi pro jantar. Entrega rapida, em 35 min estava na porta. Marmita Fit Frango estava delicioso, tempero no ponto. Recomendo!

Aspectos: {"sabor": "pos", "tempo_entrega": "pos"}

### rev_000051 — rest_004 — nota 3 — 2026-08-18

Pedido de Feijoada Individual: Entrega rápida, em 34 min estava na porta. Feijoada Individual estava delicioso, tempero no ponto. Veio frio e murcho, decepção.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos", "temperatura": "neg"}

### rev_000054 — rest_004 — nota 3 — 2026-10-13

primeira vez pedindo aqui. strogonoff veio sem tempero, bem sem graça. foi razoável.

Aspectos: {"sabor": "neg"}

### rev_000003 — rest_005 — nota 1 — 2026-08-04

Pedi Açaí 500ml. Chegou frio, tive que esquentar no micro-ondas. Ingredientes de Açaí 500ml pareciam velhos, gosto ruim. Não recomendo.

Aspectos: {"sabor": "neg", "temperatura": "neg"}

### rev_000005 — rest_005 — nota 2 — 2026-08-23

Primeira vez pedindo aqui. Açaí 500ml muito salgado, difícil de comer. Vou pensar duas vezes antes de pedir de novo.

Aspectos: {"sabor": "neg"}

### rev_000006 — rest_005 — nota 4 — 2026-08-12

Pontual, chegou no horário combinado. Preço justo pelo que entrega. Açaí 300ml estava delicioso, tempero no ponto. Açaí 300ml chegou amassado, embalagem fraca demais.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos", "embalagem": "neg", "preco": "pos"}

### rev_000012 — rest_005 — nota 3 — 2026-09-12

Primeira vez pedindo aqui. Atendimento atencioso, resolveram rápido. Entrega rápida, em 29 min estava na porta. Qualidade excelente em Açaí 300ml, ingredientes frescos. Açaí 300ml chegou gelado, claramente ficou parado esperando. Dá pra melhorar.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos", "temperatura": "neg", "atendimento": "pos"}

### rev_000014 — rest_005 — nota 3 — 2026-10-12

Pedi Vitamina de Morango. Esperei mais de uma hora pelo pedido, atraso absurdo. Vitamina de Morango tem gosto de comida caseira, caprichado. Dá pra melhorar.

Aspectos: {"sabor": "pos", "tempo_entrega": "neg"}

### rev_000023 — rest_005 — nota 4 — 2026-09-13

Pedido de Vitamina de Morango: O sabor de Vitamina de Morango surpreendeu, muito bem feito. Já virou meu pedido fixo.

Aspectos: {"sabor": "pos"}

### rev_000002 — rest_006 — nota 3 — 2026-10-19

Pedi pro jantar. Embalagem térmica e organizada, nota 10. Lasanha Bolonhesa tem gosto de comida caseira, caprichado. Preço justo pelo que entrega. Prazo estourou, chegou quase 76 minutos depois do combinado. Temperatura perfeita, nada de comida morna. Foi razoável.

Aspectos: {"sabor": "pos", "tempo_entrega": "neg", "temperatura": "pos", "embalagem": "pos", "preco": "pos"}

### rev_000004 — rest_006 — nota 3 — 2026-10-05

Pedido de Ravióli de Queijo: Chegou quentinho, como se tivesse saído do forno. Embalagem bem vedada, nada vazou. Qualidade excelente em Ravióli de Queijo, ingredientes frescos. Demorou 108 minutos, muito além do prazo informado.

Aspectos: {"sabor": "pos", "tempo_entrega": "neg", "temperatura": "pos", "embalagem": "pos"}

### rev_000017 — rest_006 — nota 3 — 2026-10-29

embalagem térmica e organizada, nota 10. entrega rápida, em 24 min estava na porta.

Aspectos: {"tempo_entrega": "pos", "embalagem": "pos"}

### rev_000027 — rest_006 — nota 4 — 2026-08-12

Pedido de Ravióli de Queijo: Chegou em 28 minutos, bem antes do previsto. Muito bem embalado, chegou intacto. Já virou meu pedido fixo.

Aspectos: {"tempo_entrega": "pos", "embalagem": "pos"}

### rev_000043 — rest_006 — nota 2 — 2026-09-07

Pedi pro jantar. Fettuccine Alfredo chegou gelado, claramente ficou parado esperando. Fettuccine Alfredo tem gosto de comida caseira, caprichado. Não recomendo.

Aspectos: {"sabor": "pos", "temperatura": "neg"}

### rev_000047 — rest_006 — nota 5 — 2026-10-21

Pedi pro jantar. Entrega rápida, em 35 min estava na porta. Ravióli de Queijo estava delicioso, tempero no ponto.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos"}

### rev_000007 — rest_007 — nota 4 — 2026-10-05

primeira vez pedindo aqui. chegou em 35 minutos, bem antes do previsto. já virou meu pedido fixo.

Aspectos: {"tempo_entrega": "pos"}

### rev_000009 — rest_007 — nota 5 — 2026-09-03

Pedido de Prato Executivo Picanha: Bebida gelada e comida quente, tudo certo. Embalagem bem vedada, nada vazou. Chegou em 20 minutos, bem antes do previsto. Qualidade excelente em Prato Executivo Picanha, ingredientes frescos.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos", "temperatura": "pos", "embalagem": "pos"}

### rev_000016 — rest_007 — nota 5 — 2026-08-08

Pontual, chegou no horário combinado. Muito bem embalado, chegou intacto. Espetinho Misto tem gosto de comida caseira, caprichado. Nota 10.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos", "embalagem": "pos"}

### rev_000024 — rest_007 — nota 5 — 2026-08-18

Pedi Prato Executivo Picanha. Prato Executivo Picanha estava delicioso, tempero no ponto. Embalagem bem vedada, nada vazou. Chegou quentinho, como se tivesse saído do forno. Já virou meu pedido fixo.

Aspectos: {"sabor": "pos", "temperatura": "pos", "embalagem": "pos"}

### rev_000026 — rest_007 — nota 5 — 2026-09-12

Restaurante muito educado no contato. Chegou quentinho, como se tivesse saído do forno. Espetinho Misto tem gosto de comida caseira, caprichado.

Aspectos: {"sabor": "pos", "temperatura": "pos", "atendimento": "pos"}

### rev_000028 — rest_007 — nota 5 — 2026-09-19

Pedi pro jantar. Chegou em 20 minutos, bem antes do previsto. Qualidade excelente em Prato Executivo Picanha, ingredientes frescos. Chegou quentinho, como se tivesse saído do forno.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos", "temperatura": "pos"}

### rev_000011 — rest_008 — nota 2 — 2026-08-29

Pedi Bolo de Pote. Chegou frio, tive que esquentar no micro-ondas. Bolo de Pote tem gosto de comida caseira, caprichado. Vou pensar duas vezes antes de pedir de novo.

Aspectos: {"sabor": "pos", "temperatura": "neg"}

### rev_000022 — rest_008 — nota 2 — 2026-08-13

Primeira vez pedindo aqui. Pedido chegou todo derramado, embalagem péssima. Chegou quentinho, como se tivesse saído do forno. Entrega rápida, em 24 min estava na porta. Bolo de Pote veio sem tempero, bem sem graça.

Aspectos: {"sabor": "neg", "tempo_entrega": "pos", "temperatura": "pos", "embalagem": "neg"}

### rev_000035 — rest_008 — nota 4 — 2026-09-27

Pedido de Bolo de Pote: Pontual, chegou no horário combinado. Nota 10.

Aspectos: {"tempo_entrega": "pos"}

### rev_000037 — rest_008 — nota 4 — 2026-08-13

Atendimento atencioso, resolveram rápido. Entrega rápida, em 35 min estava na porta. Já virou meu pedido fixo.

Aspectos: {"tempo_entrega": "pos", "atendimento": "pos"}

### rev_000038 — rest_008 — nota 4 — 2026-10-17

Pedido de Bolo de Pote: O sabor de Bolo de Pote surpreendeu, muito bem feito. Entrega rápida, em 20 min estava na porta. Nota 10.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos"}

### rev_000041 — rest_008 — nota 3 — 2026-10-20

Pedi pro jantar. Ingredientes de Torta de Limão pareciam velhos, gosto ruim. Embalagem térmica e organizada, nota 10.

Aspectos: {"sabor": "neg", "embalagem": "pos"}

### rev_000075 — rest_002 — nota 5 — 2026-10-07

Ótimo custo-benefício, porção generosa. Qualidade excelente em X-Salada, ingredientes frescos. Pontual, chegou no horário combinado. Restaurante muito educado no contato. Já virou meu pedido fixo.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos", "preco": "pos", "atendimento": "pos"}

### rev_000058 — rest_004 — nota 3 — 2026-09-07

Pedi pro jantar. Preço justo pelo que entrega. Strogonoff tem gosto de comida caseira, caprichado. Chegou em 24 minutos, bem antes do previsto. Comida morna, perdeu totalmente a graça. Dá pra melhorar.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos", "temperatura": "neg", "preco": "pos"}


## 50 exemplos revisados

### rev_000012 — rest_001 — nota 5 — 2026-10-02

O pedido levou só 23 minutos pra chegar. A embalagem veio bem fechada. Aqui em casa todo mundo gostou de pizza margherita.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos", "embalagem": "pos"}

### rev_000023 — rest_001 — nota 5 — 2026-08-08

Valeu o que paguei por pizza quatro queijos. Chegou no horário que o app mostrou. Chegou quente, deu pra comer na hora

Aspectos: {"tempo_entrega": "pos", "temperatura": "pos", "preco": "pos"}

### rev_000031 — rest_001 — nota 5 — 2026-09-07

Achei o preço justo. O gosto de pizza margherita me surpreendeu pra melhor.

Aspectos: {"sabor": "pos", "preco": "pos"}

### rev_000053 — rest_001 — nota 4 — 2026-08-25

Resolvi experimentar pizza calabresa. Tudo bem acomodado, sem embalagem aberta. O sabor de pizza calabresa valeu o pedido.

Aspectos: {"sabor": "pos", "embalagem": "pos"}

### rev_000060 — rest_001 — nota 4 — 2026-10-21

O pedido levou só 20 minutos pra chegar.

Aspectos: {"tempo_entrega": "pos"}

### rev_000085 — rest_001 — nota 2 — 2026-10-26

Precisam melhorar essa embalagem de pizza quatro queijos. Já pedi pizza quatro queijos antes e dessa vez o sabor estava pior. Chegou quente, deu pra comer na hora.

Aspectos: {"sabor": "neg", "temperatura": "pos", "embalagem": "neg"}

### rev_000001 — rest_002 — nota 1 — 2026-10-29

Já é a segunda vez que peço aqui. O preço subiu demais. burger duplo estava com um gosto ruim no final. O prazo passou e o pedido nada de chegar.

Aspectos: {"sabor": "neg", "tempo_entrega": "neg", "preco": "neg"}

### rev_000003 — rest_002 — nota 4 — 2026-09-14

Dava pra ver o cuidado com a embalagem. Fiquei esperando 112 min pelo pedido. Aqui em casa todo mundo gostou de x-bacon. O preço de x-bacon estava bom.

Aspectos: {"sabor": "pos", "tempo_entrega": "neg", "embalagem": "pos", "preco": "pos"}

### rev_000016 — rest_002 — nota 5 — 2026-10-25

Ainda estava quentinho quando abri. O valor coube no bolso

Aspectos: {"temperatura": "pos", "preco": "pos"}

### rev_000017 — rest_002 — nota 4 — 2026-09-06

O gosto de x-bacon me surpreendeu pra melhor.

Aspectos: {"sabor": "pos"}

### rev_000020 — rest_002 — nota 3 — 2026-10-09

Recebi agora meu pedido. Gostei bastante do sabor de x-bacon. A embalagem protegeu bem x-bacon. Fiquei esperando 90 min pelo pedido.

Aspectos: {"sabor": "pos", "tempo_entrega": "neg", "embalagem": "pos"}

### rev_000022 — rest_002 — nota 1 — 2026-10-23

O pedido levou 88 min e eu já estava desistindo. Ainda estava quentinho quando abri. Achei x-salada bem sem graça. Foi uma experiência ruim.

Aspectos: {"sabor": "neg", "tempo_entrega": "neg", "temperatura": "pos"}

### rev_000015 — rest_003 — nota 3 — 2026-08-20

A entrega demorou demais, deu 75 minutos. Nada a reclamar do sabor de yakisoba.

Aspectos: {"sabor": "pos", "tempo_entrega": "neg"}

### rev_000030 — rest_003 — nota 5 — 2026-08-19

Sobre hot roll: Chegou no horário que o app mostrou. Achei hot roll uma delícia. Pelo valor, achei uma boa compra.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos", "preco": "pos"}

### rev_000033 — rest_003 — nota 3 — 2026-08-15

O sabor estava ótimo, pediria hot roll de novo. O pedido levou 70 min e eu já estava desistindo.

Aspectos: {"sabor": "pos", "tempo_entrega": "neg"}

### rev_000034 — rest_003 — nota 3 — 2026-08-09

O gosto de combo 20 peças me surpreendeu pra melhor. O restaurante ignorou minhas mensagens. O lacre estava inteiro quando recebi. A temperatura de combo 20 peças estava boa.

Aspectos: {"sabor": "pos", "temperatura": "pos", "embalagem": "pos", "atendimento": "neg"}

### rev_000044 — rest_003 — nota 3 — 2026-10-02

O sabor de temaki salmao deixou a desejar. Embalagem firme, nada ficou solto.

Aspectos: {"sabor": "neg", "embalagem": "pos"}

### rev_000055 — rest_003 — nota 2 — 2026-10-13

esperava mais do sabor de hot roll.

Aspectos: {"sabor": "neg"}

### rev_000004 — rest_004 — nota 4 — 2026-10-24

Nada a reclamar do sabor de marmita executiva.

Aspectos: {"sabor": "pos"}

### rev_000006 — rest_004 — nota 3 — 2026-08-06

Gostei de como embalaram feijoada individual. Tive que esquentar feijoada individual no micro-ondas.

Aspectos: {"temperatura": "neg", "embalagem": "pos"}

### rev_000011 — rest_004 — nota 5 — 2026-10-13

Meu pedido foi feijoada individual. O lacre estava inteiro quando recebi. Achei o preço justo. Chegou em 34 minutos, antes do previsto. Gostei da experiência.

Aspectos: {"tempo_entrega": "pos", "embalagem": "pos", "preco": "pos"}

### rev_000014 — rest_004 — nota 1 — 2026-08-18

O pedido levou 79 min e eu já estava desistindo. O sabor estava ótimo, pediria marmita fit frango de novo. Já estava morno quando abri.

Aspectos: {"sabor": "pos", "tempo_entrega": "neg", "temperatura": "neg"}

### rev_000027 — rest_004 — nota 5 — 2026-10-12

A entrega foi rápida, uns 30 minutos. marmita fit frango ainda estava saindo fumaça.

Aspectos: {"tempo_entrega": "pos", "temperatura": "pos"}

### rev_000051 — rest_004 — nota 5 — 2026-09-23

Responderam minha dúvida rapidinho no chat. A entrega foi rápida, uns 25 minutos. Dava pra ver o cuidado com a embalagem. O sabor de feijoada individual estava muito bom. Mantiveram o calor de feijoada individual até a entrega. Pelo valor, achei uma boa compra.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos", "temperatura": "pos", "embalagem": "pos", "preco": "pos", "atendimento": "pos"}

### rev_000024 — rest_005 — nota 4 — 2026-08-29

O recipiente era fraco e chegou danificado. Gostei da porção pelo valor cobrado. Não precisei esperar muito, deu 19 min. Gostei bastante do sabor de vitamina de morango.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos", "embalagem": "neg", "preco": "pos"}

### rev_000041 — rest_005 — nota 4 — 2026-09-07

Achei o preco justo. Precisam melhorar essa embalagem de vitamina de morango. Falei com o restaurante e foram bem prestativos. Dessa vez acertaram no sabor de vitamina de morango.

Aspectos: {"sabor": "pos", "embalagem": "neg", "preco": "pos", "atendimento": "pos"}

### rev_000046 — rest_005 — nota 5 — 2026-08-06

açaí 500ml chegou na temperatura que eu esperava. O preço de açaí 500ml estava bom. Responderam minha dúvida rapidinho no chat.

Aspectos: {"temperatura": "pos", "preco": "pos", "atendimento": "pos"}

### rev_000056 — rest_005 — nota 5 — 2026-08-18

vitamina de morango estava uma delícia, gostei até o fim.

Aspectos: {"sabor": "pos"}

### rev_000058 — rest_005 — nota 3 — 2026-08-13

Achei açaí 300ml uma delícia. A porção de açaí 300ml era pequena pro preço.

Aspectos: {"sabor": "pos", "preco": "neg"}

### rev_000059 — rest_005 — nota 5 — 2026-09-06

Achei açaí 500ml uma delícia. Entregaram dentro do prazo.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos"}

### rev_000005 — rest_006 — nota 4 — 2026-10-12

A embalagem protegeu bem nhoque ao sugo. O sabor de nhoque ao sugo estava muito bom.

Aspectos: {"sabor": "pos", "embalagem": "pos"}

### rev_000007 — rest_006 — nota 4 — 2026-10-05

O sabor de ravióli de queijo estava muito bom. Esperei quase duas horas e já tinha passado da previsão. Veio quente como eu esperava. Embalagem firme, nada ficou solto.

Aspectos: {"sabor": "pos", "tempo_entrega": "neg", "temperatura": "pos", "embalagem": "pos"}

### rev_000021 — rest_006 — nota 3 — 2026-09-29

Pedi fettuccine alfredo. fettuccine alfredo estava uma delícia, gostei até o fim. Mais de uma hora esperando, muito além do combinado. Dá pra melhorar.

Aspectos: {"sabor": "pos", "tempo_entrega": "neg"}

### rev_000026 — rest_006 — nota 5 — 2026-10-27

O sabor estava ótimo, pediria nhoque ao sugo de novo. Chegou em 31 minutos, antes do previsto. Pediria novamente.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos"}

### rev_000029 — rest_006 — nota 5 — 2026-09-27

O entregador chegou em 19 minutos.

Aspectos: {"tempo_entrega": "pos"}

### rev_000037 — rest_006 — nota 4 — 2026-09-06

Em 28 min já estava aqui.

Aspectos: {"tempo_entrega": "pos"}

### rev_000002 — rest_007 — nota 3 — 2026-10-04

A embalagem não segurou linguiça artesanal, veio tudo bagunçado. Em 26 min já estava aqui. O gosto de linguiça artesanal me surpreendeu pra melhor.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos", "embalagem": "neg"}

### rev_000010 — rest_007 — nota 4 — 2026-10-12

Consegui falar com o restaurante sem dificuldade. linguiça artesanal veio com o sabor que eu esperava. Vou pedir de novo.

Aspectos: {"sabor": "pos", "atendimento": "pos"}

### rev_000013 — rest_007 — nota 4 — 2026-10-05

Chegou no horário que o app mostrou.

Aspectos: {"tempo_entrega": "pos"}

### rev_000018 — rest_007 — nota 5 — 2026-10-25

Foi minha primeira compra aqui. Nada a reclamar do sabor de espetinho misto. A entrega foi rápida, uns 27 minutos. Recomendo esse lugar.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos"}

### rev_000042 — rest_007 — nota 4 — 2026-10-15

pelo sabor, não pediria linguiça artesanal de novo. o pedido levou só 18 minutos pra chegar. mantiveram o calor de linguiça artesanal até a entrega. veio numa embalagem bem resistente.

Aspectos: {"sabor": "neg", "tempo_entrega": "pos", "temperatura": "pos", "embalagem": "pos"}

### rev_000063 — rest_007 — nota 5 — 2026-08-28

Pedido feito e entregue em 32 min. Nada a reclamar do sabor de prato executivo picanha.

Aspectos: {"sabor": "pos", "tempo_entrega": "pos"}

### rev_000008 — rest_008 — nota 3 — 2026-10-21

Fiquei esperando 118 min pelo pedido.

Aspectos: {"tempo_entrega": "neg"}

### rev_000009 — rest_008 — nota 4 — 2026-08-26

Veio protegido do calor, como deveria.

Aspectos: {"temperatura": "pos"}

### rev_000019 — rest_008 — nota 5 — 2026-10-13

O sabor de bolo de pote estava muito bom. O preço de bolo de pote estava bom.

Aspectos: {"sabor": "pos", "preco": "pos"}

### rev_000025 — rest_008 — nota 1 — 2026-08-23

Foi minha primeira compra aqui. O gosto de torta de limão estava bem diferente do habitual. A embalagem rasgou no caminho.

Aspectos: {"sabor": "neg", "embalagem": "neg"}

### rev_000035 — rest_008 — nota 5 — 2026-08-15

O sabor de brigadeiro gourmet estava muito bom. O atendimento foi atencioso. Vou pedir de novo.

Aspectos: {"sabor": "pos", "atendimento": "pos"}

### rev_000038 — rest_008 — nota 1 — 2026-08-13

Dessa vez chegou rapidinho, em 35 minutos. Não fecharam direito a embalagem. Veio refrigerado como deveria. Não consegui terminar bolo de pote, o gosto não estava bom.

Aspectos: {"sabor": "neg", "tempo_entrega": "pos", "temperatura": "pos", "embalagem": "neg"}

### rev_000028 — rest_002 — nota 5 — 2026-09-14

A embalagem veio bem fechada. Chegou no horário que o app mostrou. Consegui falar com o restaurante sem dificuldade

Aspectos: {"tempo_entrega": "pos", "embalagem": "pos", "atendimento": "pos"}

### rev_000052 — rest_004 — nota 3 — 2026-09-01

O recipiente era fraco e chegou danificado. O preço de feijoada individual estava bom. Dá pra melhorar.

Aspectos: {"embalagem": "neg", "preco": "pos"}
