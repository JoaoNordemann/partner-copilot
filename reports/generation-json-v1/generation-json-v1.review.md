# Revisao do JSON: pendente

Revisor: ____ Origem: ____

Aceitacao pelo parser nao comprova resposta pertinente ou factual.

| Pergunta | Aceita pelo parser | Sustentada para a pergunta (leitura) |
| --- | --- | --- |
| n01 | True | pendente |
| n02 | False | pendente |
| n03 | False | pendente |
| n04 | True | pendente |
| n05 | True | pendente |
| n06 | True | pendente |
| n07 | True | pendente |
| n08 | False | pendente |
| n09 | True | pendente |
| n10 | True | pendente |

## n01

Pergunta: Que avaliacao elogia a porcao da Pizza Calabresa em relacao ao valor cobrado?

Sustentacao factual: ____
Abstencao adequada: ____
Observacoes: ____

Resposta bruta:
```json
{"abstem":false,"afirmacoes":[{"texto":"Gostei da porção da pizza Calabresa pelo valor cobrado.", "review_ids":["rev_001076"]}]}
```

Contexto:
- rev_001076: "Pedi pizza calabresa. Gostei da porção pelo valor cobrado. Pelo sabor, não pediria pizza calabresa de novo."
- rev_002549: "O atendimento no chat foi bem ruim. Gostei de como embalaram pizza calabresa."
- rev_000813: "Já estava morno quando abri. A sacola estava lacrada e tudo no lugar. Já pedi pizza calabresa antes e dessa vez o sabor estava pior. Não valeu a pena."

## n02

Pergunta: Que elogio ao custo-beneficio aparece nas avaliacoes do Burger Duplo?

Sustentacao factual: ____
Abstencao adequada: ____
Observacoes: ____

Resposta bruta:
```json
{"abstem":false,"afirmacoes":[{"texto":"Pelo valor, achei uma boa compra.", "review_ids":["rev_000799"]},{"texto":"Achei uma boa compra pelo valor.", "review_ids":["rev_000799"]}]}

Fonte: <AVALIACOES_JSONL>
{"review_id":"rev_000799","restaurant_id":"rest_002","item":"Burger Duplo","created_at":"2026-09-24","rating":5,"text":"Não precisei esquentar burger duplo. burger duplo estava uma delícia, gostei até o fim. Pelo valor, achei uma boa compra.", "chunk_index":0, "chunk_count":1}
```

Contexto:
- rev_000799: "Não precisei esquentar burger duplo. burger duplo estava uma delícia, gostei até o fim. Pelo valor, achei uma boa compra."
- rev_002257: "Demoraram demais pra responder minha dúvida. O sabor de burger duplo estava muito bom."

## n03

Pergunta: Que comentarios favoraveis ao preco do Hot Roll foram registrados?

Sustentacao factual: ____
Abstencao adequada: ____
Observacoes: ____

Resposta bruta:
```json
{"abstem":false,"afirmacoes":[{"texto":"O preço de hot roll estava bom.", "review_ids":["rev_002759"]},
 {"texto":"O valor coube no bolso.", "review_ids":["rev_002759"]}]}

Fonte: <AVALIACOES_JSONL>
(As afirmações são sustentadas pelas revisões identificadas pelos seus IDs)
```

Contexto:
- rev_001629: "Meu pedido foi hot roll. O preço de hot roll estava bom. Veio frio, perdeu bastante a graça. hot roll estava uma delícia, gostei até o fim. A entrega foi rápida, uns 35 minutos."
- rev_002759: "O valor coube no bolso. Dessa vez acertaram no sabor de hot roll. A embalagem protegeu bem hot roll. Recomendo esse lugar."
- rev_001729: "Resolvi experimentar hot roll. O lacre estava inteiro quando recebi. Recomendo esse lugar."

## n04

Pergunta: Ha relato de entrega antes do previsto para a Marmita Fit Frango? Qual foi o tempo?

Sustentacao factual: ____
Abstencao adequada: ____
Observacoes: ____

Resposta bruta:
```json
{"abstem": false, "afirmacoes": [{"texto": "A Marmita Fit Frango chegou em 26 minutos, antes do previsto.", "review_ids": ["rev_000400"]}]}
```

Contexto:
- rev_000400: "Chegou em 26 minutos, antes do previsto. Não gostei do sabor de marmita fit frango. marmita fit frango chegou bem quente."

## n05

Pergunta: Qual relato cita entrega de Copo da Felicidade em cerca de vinte minutos?

Sustentacao factual: ____
Abstencao adequada: ____
Observacoes: ____

Resposta bruta:
```json
{"abstem":false,"afirmacoes":[{"texto":"A entrega de Copo da Felicidade foi em aproximadamente vinte minutos.", "review_ids":["rev_002370"]}]}
```

Contexto:
- rev_002370: "Sobre copo da felicidade: A entrega foi rápida, uns 20 minutos. Não achei caro pelo que veio. Veio refrigerado como deveria. Pediria novamente."
- rev_001478: "Meu pedido foi copo da felicidade. copo da felicidade estava uma delícia, gostei até o fim."
- rev_001265: "O restaurante ignorou minhas mensagens. copo da felicidade estava uma delícia, gostei até o fim."

## n06

Pergunta: Ha um relato favoravel ao preco do Nhoque ao Sugo? O que diz?

Sustentacao factual: ____
Abstencao adequada: ____
Observacoes: ____

Resposta bruta:
```json
{"abstem":false,"afirmacoes":[{"texto":"O valor de Nhoque ao Sugo foi considerado válido pelo cliente.", "review_ids":["rev_002933"]}]}
```

Contexto:
- rev_002800: "Sobre nhoque ao sugo: O gosto de nhoque ao sugo estava bem diferente do habitual. Embalagem firme, nada ficou solto. Em 20 min já estava aqui. Algumas coisas precisam melhorar"
- rev_000300: "Dessa vez acertaram no sabor de nhoque ao sugo. Pediria novamente."
- rev_002933: "O valor coube no bolso. A entrega foi rápida, uns 32 minutos"

## n07

Pergunta: Em qual review de Bolo de Pote a loja foi descrita como prestativa?

Sustentacao factual: ____
Abstencao adequada: ____
Observacoes: ____

Resposta bruta:
```json
{"abstem":false,"afirmacoes":[{"texto":"Falei com o restaurante e foram bem prestativos.","review_ids":["rev_002787"]}]}
```

Contexto:
- rev_002787: "Achei bolo de pote uma delícia. Falei com o restaurante e foram bem prestativos. Tudo bem acomodado, sem embalagem aberta. Pelo valor, achei uma boa compra. A temperatura de bolo de pote estava boa. Valeu a compra."
- rev_002127: "A tampa veio solta, não gostei disso. O sabor de bolo de pote valeu o pedido. Chegou fresco e bem refrigerado. Dá pra melhorar."
- rev_000445: "Não achei caro pelo que veio. O sabor de bolo de pote estava muito bom. Entregaram dentro do prazo. Veio sem lacre na sacola."
- rev_002490: "Sobre bolo de pote: Veio sem refrigeração, já estava morno. O sabor estava ótimo, pediria bolo de pote de novo. O preço subiu demais. Não valeu a pena"

## n08

Pergunta: Qual numero de lote industrial do Copo da Felicidade foi informado nas avaliacoes?

Sustentacao factual: ____
Abstencao adequada: ____
Observacoes: ____

Resposta bruta:
```json
{"abstem":false,"afirmacoes":[{"texto":"O Copo da Felicidade foi entregue rápido em pelo menos um caso.", "review_ids":["rev_002370"]}]}

Explicação: Apenas uma afirmação é possível ser feita com base nos dados fornecidos, e ela é de natureza neutra (neither elogio nor reclamação). A afirmação é baseada na segunda avaliação, onde o revisor menciona que a entrega foi rápida. Não há nenhuma informação sobre a temperatura ou sabor do Copo da Felicidade nas avaliações fornecidas.
```

Contexto:
- rev_001478: "Meu pedido foi copo da felicidade. copo da felicidade estava uma delícia, gostei até o fim."
- rev_002370: "Sobre copo da felicidade: A entrega foi rápida, uns 20 minutos. Não achei caro pelo que veio. Veio refrigerado como deveria. Pediria novamente."
- rev_001265: "O restaurante ignorou minhas mensagens. copo da felicidade estava uma delícia, gostei até o fim."

## n09

Pergunta: Qual laboratorio realizou a analise microbiologica do Yakisoba segundo as reviews?

Sustentacao factual: ____
Abstencao adequada: ____
Observacoes: ____

Resposta bruta:
```json
{"abstem":false,"afirmacoes":[{"texto":"A Yakisoba foi analisada microbiologicamente em algum laboratorio, mas a revisao nao fornece informacao suficiente para identificar qual laboratorio foi utilizado.", "review_ids":["rev_002142"]}]}
```

Contexto:
- rev_002142: "Ainda estava quentinho quando abri. Gostei muito de yakisoba. Bom custo-beneficio nesse yakisoba. A entrega demorou demais, deu 115 minutos"

## n10

Pergunta: Qual CNPJ foi informado nas avaliacoes do restaurante rest_007?

Sustentacao factual: ____
Abstencao adequada: ____
Observacoes: ____

Resposta bruta:
```json
{"abstem":false,"afirmacoes":[{"texto":"Nenhuma avaliação menciona o CNPJ do restaurante.", "review_ids":["rev_002476", "rev_001715", "rev_002417", "rev_001027"]}]}
```

Contexto:
- rev_002476: "Gostei muito de prato executivo picanha. Pedi com antecedência e mesmo assim atrasou bastante."
- rev_001715: "Resolvi experimentar prato executivo picanha. prato executivo picanha chegou bem quente. Não achei o preço justo. Não pediria de novo."
- rev_002417: "Foi minha primeira compra aqui. O atendimento foi atencioso. O sabor de espetinho misto deixou a desejar. Algumas coisas precisam melhorar."
- rev_001027: "Foi minha primeira compra aqui. Levou 79 minutos pra chegar, passou bastante do prazo. O sabor estava ótimo, pediria costela no bafo de novo."
