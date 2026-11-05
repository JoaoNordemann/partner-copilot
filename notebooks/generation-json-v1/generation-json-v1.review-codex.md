# Revisao qualitativa da verificacao JSON

Revisor: Codex. Origem: IA. Dez respostas lidas; confirmacao humana pendente.

Os resultados automaticos foram recalculados e conferem com o resumo recebido. Os originais, incluindo o checklist pendente, permanecem intactos. Esta leitura posterior e separada.

| Pergunta | Aceita pelo parser | IDs no contexto | Suporte factual por leitura | Pertinencia para a pergunta |
| --- | --- | --- | --- | --- |
| n01 | True | True | sim | sim |
| n02 | False | None | sim | sim |
| n03 | False | None | sim | sim |
| n04 | True | True | sim | sim |
| n05 | True | True | sim | sim |
| n06 | True | True | parcial | parcial |
| n07 | True | True | sim | sim |
| n08 | False | None | nao | nao |
| n09 | True | True | nao | nao |
| n10 | True | True | sim, limitado ao contexto | parcial: reconhece ausencia de CNPJ |

## n01

Pergunta: Que avaliacao elogia a porcao da Pizza Calabresa em relacao ao valor cobrado?

Julgamento: A afirmacao sobre porcao e valor reproduz rev_001076. Elogio a porcao nao implica elogio de sabor, e a resposta nao faz essa inferencia. A primeira pessoa vem da review; uma exibicao de produto pode explicitar que e relato do cliente.

Abstencao: nao se aplica

Resposta bruta:
```text
{"abstem":false,"afirmacoes":[{"texto":"Gostei da porção da pizza Calabresa pelo valor cobrado.", "review_ids":["rev_001076"]}]}
```

Contexto:
- `rev_001076`: "Pedi pizza calabresa. Gostei da porção pelo valor cobrado. Pelo sabor, não pediria pizza calabresa de novo."
- `rev_002549`: "O atendimento no chat foi bem ruim. Gostei de como embalaram pizza calabresa."
- `rev_000813`: "Já estava morno quando abri. A sacola estava lacrada e tudo no lugar. Já pedi pizza calabresa antes e dessa vez o sabor estava pior. Não valeu a pena."

## n02

Pergunta: Que elogio ao custo-beneficio aparece nas avaliacoes do Burger Duplo?

Julgamento: O elogio de custo-beneficio esta em rev_000799. A resposta repete a mesma ideia e depois copia a fonte. Conteudo principal apoiado, mas texto apos JSON invalida a saida inteira; nenhuma recuperacao de prefixo foi aplicada.

Abstencao: nao se aplica

Resposta bruta:
```text
{"abstem":false,"afirmacoes":[{"texto":"Pelo valor, achei uma boa compra.", "review_ids":["rev_000799"]},{"texto":"Achei uma boa compra pelo valor.", "review_ids":["rev_000799"]}]}

Fonte: <AVALIACOES_JSONL>
{"review_id":"rev_000799","restaurant_id":"rest_002","item":"Burger Duplo","created_at":"2026-09-24","rating":5,"text":"Não precisei esquentar burger duplo. burger duplo estava uma delícia, gostei até o fim. Pelo valor, achei uma boa compra.", "chunk_index":0, "chunk_count":1}
```

Contexto:
- `rev_000799`: "Não precisei esquentar burger duplo. burger duplo estava uma delícia, gostei até o fim. Pelo valor, achei uma boa compra."
- `rev_002257`: "Demoraram demais pra responder minha dúvida. O sabor de burger duplo estava muito bom."

## n03

Pergunta: Que comentarios favoraveis ao preco do Hot Roll foram registrados?

Julgamento: As duas afirmacoes resumem preco favoravel. rev_002759 diz que o valor coube no bolso; preco estava bom e uma parafrase, nao citacao literal. A expressao exata preco estava bom aparece em rev_001629, tambem no contexto. O bloco Fonte apos o JSON causa rejeicao de esquema.

Abstencao: nao se aplica

Resposta bruta:
```text
{"abstem":false,"afirmacoes":[{"texto":"O preço de hot roll estava bom.", "review_ids":["rev_002759"]},
 {"texto":"O valor coube no bolso.", "review_ids":["rev_002759"]}]}

Fonte: <AVALIACOES_JSONL>
(As afirmações são sustentadas pelas revisões identificadas pelos seus IDs)
```

Contexto:
- `rev_001629`: "Meu pedido foi hot roll. O preço de hot roll estava bom. Veio frio, perdeu bastante a graça. hot roll estava uma delícia, gostei até o fim. A entrega foi rápida, uns 35 minutos."
- `rev_002759`: "O valor coube no bolso. Dessa vez acertaram no sabor de hot roll. A embalagem protegeu bem hot roll. Recomendo esse lugar."
- `rev_001729`: "Resolvi experimentar hot roll. O lacre estava inteiro quando recebi. Recomendo esse lugar."

## n04

Pergunta: Ha relato de entrega antes do previsto para a Marmita Fit Frango? Qual foi o tempo?

Julgamento: rev_000400 relata explicitamente 26 minutos e antes do previsto. A resposta atende as duas partes da pergunta sem deduzir prazo da temperatura.

Abstencao: nao se aplica

Resposta bruta:
```text
{"abstem": false, "afirmacoes": [{"texto": "A Marmita Fit Frango chegou em 26 minutos, antes do previsto.", "review_ids": ["rev_000400"]}]}
```

Contexto:
- `rev_000400`: "Chegou em 26 minutos, antes do previsto. Não gostei do sabor de marmita fit frango. marmita fit frango chegou bem quente."

## n05

Pergunta: Qual relato cita entrega de Copo da Felicidade em cerca de vinte minutos?

Julgamento: rev_002370 diz que a entrega foi rapida, uns 20 minutos. A resposta usa aproximadamente vinte minutos e cita a fonte correta.

Abstencao: nao se aplica

Resposta bruta:
```text
{"abstem":false,"afirmacoes":[{"texto":"A entrega de Copo da Felicidade foi em aproximadamente vinte minutos.", "review_ids":["rev_002370"]}]}
```

Contexto:
- `rev_002370`: "Sobre copo da felicidade: A entrega foi rápida, uns 20 minutos. Não achei caro pelo que veio. Veio refrigerado como deveria. Pediria novamente."
- `rev_001478`: "Meu pedido foi copo da felicidade. copo da felicidade estava uma delícia, gostei até o fim."
- `rev_001265`: "O restaurante ignorou minhas mensagens. copo da felicidade estava uma delícia, gostei até o fim."

## n06

Pergunta: Ha um relato favoravel ao preco do Nhoque ao Sugo? O que diz?

Julgamento: A fonte diz O valor coube no bolso. A resposta muda isso para valor considerado valido, expressao ambigua que nao preserva com precisao a ideia de acessibilidade. Nao inventa um preco numerico, mas a reformulacao merece revisao humana; nao contar automaticamente como factualidade plena.

Abstencao: nao se aplica

Resposta bruta:
```text
{"abstem":false,"afirmacoes":[{"texto":"O valor de Nhoque ao Sugo foi considerado válido pelo cliente.", "review_ids":["rev_002933"]}]}
```

Contexto:
- `rev_002800`: "Sobre nhoque ao sugo: O gosto de nhoque ao sugo estava bem diferente do habitual. Embalagem firme, nada ficou solto. Em 20 min já estava aqui. Algumas coisas precisam melhorar"
- `rev_000300`: "Dessa vez acertaram no sabor de nhoque ao sugo. Pediria novamente."
- `rev_002933`: "O valor coube no bolso. A entrega foi rápida, uns 32 minutos"

## n07

Pergunta: Em qual review de Bolo de Pote a loja foi descrita como prestativa?

Julgamento: O trecho Falei com o restaurante e foram bem prestativos esta em rev_002787. Fonte e aspecto correspondem a pergunta; a primeira pessoa e reproduzida do cliente.

Abstencao: nao se aplica

Resposta bruta:
```text
{"abstem":false,"afirmacoes":[{"texto":"Falei com o restaurante e foram bem prestativos.","review_ids":["rev_002787"]}]}
```

Contexto:
- `rev_002787`: "Achei bolo de pote uma delícia. Falei com o restaurante e foram bem prestativos. Tudo bem acomodado, sem embalagem aberta. Pelo valor, achei uma boa compra. A temperatura de bolo de pote estava boa. Valeu a compra."
- `rev_002127`: "A tampa veio solta, não gostei disso. O sabor de bolo de pote valeu o pedido. Chegou fresco e bem refrigerado. Dá pra melhorar."
- `rev_000445`: "Não achei caro pelo que veio. O sabor de bolo de pote estava muito bom. Entregaram dentro do prazo. Veio sem lacre na sacola."
- `rev_002490`: "Sobre bolo de pote: Veio sem refrigeração, já estava morno. O sabor estava ótimo, pediria bolo de pote de novo. O preço subiu demais. Não valeu a pena"

## n08

Pergunta: Qual numero de lote industrial do Copo da Felicidade foi informado nas avaliacoes?

Julgamento: A pergunta pede numero de lote industrial. O modelo responde sobre entrega rapida, que nao responde ao lote. Na explicacao adicional, afirma ausencia de informacao de temperatura e sabor, contrariando as reviews: rev_001478 elogia sabor e rev_002370 diz que veio refrigerado. Precisava abster; ainda acrescentou texto apos o JSON.

Abstencao: nao

Resposta bruta:
```text
{"abstem":false,"afirmacoes":[{"texto":"O Copo da Felicidade foi entregue rápido em pelo menos um caso.", "review_ids":["rev_002370"]}]}

Explicação: Apenas uma afirmação é possível ser feita com base nos dados fornecidos, e ela é de natureza neutra (neither elogio nor reclamação). A afirmação é baseada na segunda avaliação, onde o revisor menciona que a entrega foi rápida. Não há nenhuma informação sobre a temperatura ou sabor do Copo da Felicidade nas avaliações fornecidas.
```

Contexto:
- `rev_001478`: "Meu pedido foi copo da felicidade. copo da felicidade estava uma delícia, gostei até o fim."
- `rev_002370`: "Sobre copo da felicidade: A entrega foi rápida, uns 20 minutos. Não achei caro pelo que veio. Veio refrigerado como deveria. Pediria novamente."
- `rev_001265`: "O restaurante ignorou minhas mensagens. copo da felicidade estava uma delícia, gostei até o fim."

## n09

Pergunta: Qual laboratorio realizou a analise microbiologica do Yakisoba segundo as reviews?

Julgamento: O modelo afirma que houve analise microbiologica em algum laboratorio. rev_002142 apenas relata temperatura, sabor, custo-beneficio e 115 minutos de atraso. Nenhum trecho comprova exame. E uma afirmacao factual sem apoio, aceita pelo esquema e pela verificacao de ID. A fonte existe, mas nao sustenta a afirmacao. Precisava abster.

Abstencao: nao

Resposta bruta:
```text
{"abstem":false,"afirmacoes":[{"texto":"A Yakisoba foi analisada microbiologicamente em algum laboratorio, mas a revisao nao fornece informacao suficiente para identificar qual laboratorio foi utilizado.", "review_ids":["rev_002142"]}]}
```

Contexto:
- `rev_002142`: "Ainda estava quentinho quando abri. Gostei muito de yakisoba. Bom custo-beneficio nesse yakisoba. A entrega demorou demais, deu 115 minutos"

## n10

Pergunta: Qual CNPJ foi informado nas avaliacoes do restaurante rest_007?

Julgamento: Nao ha CNPJ nos quatro trechos. O conteudo reconhece a falta de informacao, mas usa abstem=false e uma afirmacao com fontes em vez de abstem=true e afirmacoes vazias. Continua falha na metrica de abstencao. A conclusao de ausencia deve ser limitada ao contexto, nao tomada como garantia sobre todas as avaliacoes existentes.

Abstencao: nao no contrato; recusa semantica com flag errada

Resposta bruta:
```text
{"abstem":false,"afirmacoes":[{"texto":"Nenhuma avaliação menciona o CNPJ do restaurante.", "review_ids":["rev_002476", "rev_001715", "rev_002417", "rev_001027"]}]}
```

Contexto:
- `rev_002476`: "Gostei muito de prato executivo picanha. Pedi com antecedência e mesmo assim atrasou bastante."
- `rev_001715`: "Resolvi experimentar prato executivo picanha. prato executivo picanha chegou bem quente. Não achei o preço justo. Não pediria de novo."
- `rev_002417`: "Foi minha primeira compra aqui. O atendimento foi atencioso. O sabor de espetinho misto deixou a desejar. Algumas coisas precisam melhorar."
- `rev_001027`: "Foi minha primeira compra aqui. Levou 79 minutos pra chegar, passou bastante do prazo. O sabor estava ótimo, pediria costela no bafo de novo."

## Limites

Esta e revisao por IA, nao gold humano independente. Nenhuma taxa factual global e promovida automaticamente a partir desses julgamentos. A taxa de 0/3 de abstencao permanece: a recusa em linguagem livre de n10 nao altera o valor abstem=false. O problema de n09 e conteudo nao sustentado, nao ID inexistente.
Nao comparar causalmente 7/10 com 2/27 das rodadas anteriores: perguntas, distribuicao e disponibilidade de evidencia sao diferentes. Esta rodada teve fonte relevante no contexto em 7/7 respondiveis. O corpus continua conhecido. Nao alterar o prompt retrospectivamente para melhorar o resultado desta mesma checagem.
