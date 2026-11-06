# Leitura qualitativa de D

Revisor: Codex. Origem: IA. Dez casos lidos; confirmacao humana pendente.

Os estados e metricas originais foram preservados. Recusa semanticamente adequada nao equivale a abstencao valida no contrato.

| Pergunta | Suporte factual | Recusa adequada ao contexto |
| --- | --- | --- |
| q01 | sim | sim |
| q09 | nao | nao |
| q13 | sim | sim |
| q22 | nao | nao |
| q25 | parcial | sim quanto ao fato principal |
| q26 | sim, limitado ao contexto | sim quanto ao fato principal |
| q27 | sim, limitado ao contexto | sim quanto ao fato principal |
| q28 | sim, limitado ao contexto | sim quanto ao fato principal |
| q29 | sim | sim |
| q30 | sim | sim |

## q01

Pergunta: Quais reclamações sobre embalagem aparecem na Pizzaria Forno Nobre?

Nao ha reclamacao explicita de embalagem nos cinco trechos. A recusa principal e adequada, mas a lista de IDs e o marcador de colchete simples sao invalidos. A fonte relevante estava fora do contexto.

Resposta bruta:
```text
Nao ha reclamacoes explictas sobre embalagem no conjunto de dados fornecido [rev_000294, rev_002549, rev_000650, rev_000673, rev_002980] [SEM_EVIDENCIA]
```

Contexto:
- `rev_000294`: "Nada a reclamar do sabor de pizza portuguesa. Não precisei esquentar pizza portuguesa. Veio numa embalagem bem resistente."
- `rev_002980`: "Me atenderam bem quando mandei mensagem. O gosto de pizza quatro queijos estava bem diferente do habitual."
- `rev_002549`: "O atendimento no chat foi bem ruim. Gostei de como embalaram pizza calabresa."
- `rev_000673`: "Resolvi experimentar pizza quatro queijos. Demoraram demais pra responder minha dúvida. Já estava morno quando abri. Espero que melhorem."
- `rev_000650`: "A embalagem veio bem fechada. Aqui em casa todo mundo gostou de pizza margherita."

## q09

Pergunta: Quais relatos sustentam reclamações de atraso do Burger do Zé nas últimas duas semanas até 01/11/2026?

Nega atraso apesar de rev_000212 dizer Mais de uma hora esperando, muito alem do combinado. Tambem produz frases e tags em vez de IDs e marcador correto.

Resposta bruta:
```text
EXATAMENTE ["Nao ha evidencia sobre reclamos de atraso do Burger do Zé na base de dados fornecida"][[PERGUNTA_JSON]]
["Nao ha informacao sobre atraso especifico do Burger do Zé nas avaliacoes fornecidas"][["Avaliacoes_JSONL"]]
```

Contexto:
- `rev_000212`: "Ainda estava quentinho quando abri. Mais de uma hora esperando, muito além do combinado. Já pedi x-salada antes e dessa vez o sabor estava pior."

## q13

Pergunta: Quais relatos da Cantina Bella Massa mencionam espera excessiva de 19/10 a 01/11/2026?

Contexto vazio, sem nova chamada nem chamada original ao LLM. Abster e adequado ao contexto; a evidencia existente na base foi perdida pelo retrieval.

Resposta bruta:
```text
(LLM nao chamado)
Não há evidência suficiente nas avaliações fornecidas.
```

Contexto:
(vazio)

## q22

Pergunta: Quem achou a refeição da Cantina Bella Massa desagradável ao paladar?

Nega reclamacoes de sabor presentes em rev_001051 e rev_002684, alem da insatisfacao em rev_002234. A exclusao apenas por causa do sabor nao consta da pergunta. Mistura texto, lista de IDs e marcador.

Resposta bruta:
```text
Nao ha review que achou a refeicao da Cantina Bella Massa desagradavel ao paladar apenas por causa do sabor, baseado nos dados fornecidos. [rev_000300, rev_001760, rev_001051, rev_002684, rev_002234]

[[SEM_EVIDENCIA]]
```

Contexto:
- `rev_000300`: "Dessa vez acertaram no sabor de nhoque ao sugo. Pediria novamente."
- `rev_001760`: "Meu pedido foi lasanha bolonhesa. lasanha bolonhesa chegou frio. Gostei muito de lasanha bolonhesa."
- `rev_001051`: "lasanha bolonhesa não estava gostoso como das outras vezes. lasanha bolonhesa chegou frio. A embalagem veio bem fechada. Foram grossos quando entrei em contato."
- `rev_002684`: "Ja estava morno quando abri. ravioli de queijo nao estava gostoso como das outras vezes. Nao valeu a pena."
- `rev_002234`: "Chegou quente, deu pra comer na hora. Foram 92 minutos de espera, atrapalhou meu almoço. Esperava mais do sabor de ravióli de queijo."

## q25

Pergunta: Quais clientes do Burger do Zé relataram uma reação alérgica a amendoim?

Nenhum trecho relata alergia. A resposta reconhece isso, mas tambem afirma que os cinco trechos comentam embalagem, o que nao ocorre. Mantem escapes Unicode literais e nao usa o marcador exigido.

Resposta bruta:
```text
EXATAMENTE \u005b\u005bNenhuma revisao relatou reacao alergica a amendoim no restaurante do Burger Ze\u005d\u005d

Baseado na analise dos dados fornecidos em AVALIACOES\_JSONL, nenhuma revisao mencionou reacao alergica a amendoim. As revisoes apenas comentaram sobre sabor, temperatura, atraso e embalagem.
```

Contexto:
- `rev_002257`: "Demoraram demais pra responder minha dúvida. O sabor de burger duplo estava muito bom."
- `rev_002289`: "Não gostei do sabor de x-bacon. Tive que esquentar x-bacon no micro-ondas. Fiquei esperando 112 min pelo pedido"
- `rev_000799`: "Não precisei esquentar burger duplo. burger duplo estava uma delícia, gostei até o fim. Pelo valor, achei uma boa compra."
- `rev_002089`: "Meu pedido foi batata frita grande. Pelo sabor, não pediria batata frita grande de novo."
- `rev_001685`: "Pedido feito e entregue em 33 min. Não gostei do sabor de batata frita grande."

## q26

Pergunta: Qual valor de reembolso via Pix foi recebido pelos clientes do Sushi Kaze?

Nenhum trecho informa reembolso Pix. A resposta reconhece a insuficiencia, mas conserva prefixos review_ e agrupamento de IDs, sem marcador de abstencao.

Resposta bruta:
```text
EXATAMENTE, Nenhuma afirmação sustentada pelos dados fornecidos sobre o valor de reembolso via Pix recebido pelos clientes do Sushi Kaze. [review_002759, review_001998, review_002142, review_001629, review_002675]
```

Contexto:
- `rev_002759`: "O valor coube no bolso. Dessa vez acertaram no sabor de hot roll. A embalagem protegeu bem hot roll. Recomendo esse lugar."
- `rev_001998`: "A entrega demorou demais, deu 76 minutos. combo 20 peças estava com um gosto ruim no final. Capricharam na embalagem de combo 20 peças. O preço de combo 20 peças estava bom."
- `rev_002142`: "Ainda estava quentinho quando abri. Gostei muito de yakisoba. Bom custo-beneficio nesse yakisoba. A entrega demorou demais, deu 115 minutos"
- `rev_001629`: "Meu pedido foi hot roll. O preço de hot roll estava bom. Veio frio, perdeu bastante a graça. hot roll estava uma delícia, gostei até o fim. A entrega foi rápida, uns 35 minutos."
- `rev_002675`: "Pedi combo 20 peças. O valor coube no bolso. O prazo passou e o pedido nada de chegar. Algumas coisas precisam melhorar."

## q27

Pergunta: Qual é a receita completa sem glúten da Marmita Fit Frango da Dona Rosa?

Nao ha receita completa ou comprovacao de ausencia de gluten. A recusa do fato principal e adequada; fontes com prefixo errado e escapes literais continuam invalidas.

Resposta bruta:
```text
EXATAMENTE, Nenhuma afirmação sustentada pelos dados fornecidos em relação a receita completa sem glúten da Marmita Fit Frango da Dona Rosa. \u005breview_001829, review_000400, review_00345, review_002438, review_002598\u005d
```

Contexto:
- `rev_001829`: "o sabor de marmita fit frango valeu o pedido."
- `rev_000400`: "Chegou em 26 minutos, antes do previsto. Não gostei do sabor de marmita fit frango. marmita fit frango chegou bem quente."
- `rev_000345`: "O sabor de marmita executiva estava muito bom. Gostei de como embalaram marmita executiva. Em 20 min já estava aqui. Não achei caro pelo que veio. Veio frio, perdeu bastante a graça."
- `rev_002438`: "Falei com o restaurante e foram bem prestativos. Não precisei esquentar feijoada individual. Achei feijoada individual uma delícia."
- `rev_002598`: "Foi minha primeira compra aqui. O sabor de strogonoff estava muito bom. Tudo bem acomodado, sem embalagem aberta. O pedido levou só 25 minutos pra chegar. Falei com o restaurante e foram bem prestativos."

## q28

Pergunta: Quais consumidores da Doceria Ateliê Doce encontraram insetos na comida?

Nenhum trecho fala de insetos. A recusa e semanticamente adequada; o texto conserva escapes literais e cita AVALIACOES_JSONL, que nao e ID de review.

Resposta bruta:
```text
EXATAMENTE \u005b\u005bNao há evidencia sobre insetos na comida em nenhum dos reviews\u005d\u005d [AVALIACOES_JSONL]
```

Contexto:
- `rev_002833`: "Não achei o preço justo. A temperatura de brigadeiro gourmet estava adequada. Entregaram dentro do prazo. Dessa vez acertaram no sabor de brigadeiro gourmet. O pedido teve pontos bons e ruins."
- `rev_002121`: "cookie recheado veio abafado e quente demais. Não consegui terminar cookie recheado, o gosto não estava bom. Gostei de como embalaram cookie recheado."
- `rev_002355`: "Sobre torta de limão: Achei torta de limão uma delícia. Não fecharam direito a embalagem. Veio gelado e pronto pra consumir. Em 30 min já estava aqui."
- `rev_000357`: "Recebi agora meu pedido. Não precisei esperar muito, deu 18 min. O gosto de torta de limão me surpreendeu pra melhor. Demoraram demais pra responder minha dúvida."

## q29

Pergunta: Quais críticas de sabor recebeu a Pizza de Trufas da Pizzaria Forno Nobre?

Contexto vazio; absteve sem LLM. Nao atribuir o resultado a geracao do modelo.

Resposta bruta:
```text
(LLM nao chamado)
Não há evidência suficiente nas avaliações fornecidas.
```

Contexto:
(vazio)

## q30

Pergunta: Quais avaliações do Burger do Zé mencionam atrasos de 01/01 a 14/01/2030?

Contexto vazio para o periodo solicitado; absteve sem LLM. Nao houve correcao nem geracao nesse caso.

Resposta bruta:
```text
(LLM nao chamado)
Não há evidência suficiente nas avaliações fornecidas.
```

Contexto:
(vazio)
