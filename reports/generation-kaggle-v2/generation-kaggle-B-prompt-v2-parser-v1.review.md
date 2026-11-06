# Leitura de respostas reais — pendente

Gerar este arquivo não significa que as respostas foram revisadas.
Revisor: ______  Origem da revisão (humana/IA): ______

## q01

Revisada: [ ]
Suporte factual: ______
Abstenção adequada: ______
Citações sustentam afirmações: ______
Observações: ______

Pergunta: Quais reclamações sobre embalagem aparecem na Pizzaria Forno Nobre?

Resposta bruta:
"Nao ha reclamacoes sobre embalagem explictas no conjunto de dados fornecido [rev_000294, rev_002549, rev_000650, rev_000673, rev_002980].\n\n[[SEM_EVIDENCIA]]"

Erro: {"code": "generation_contract_error", "type": "GenerationContractError", "message": "Abstention marker must be the complete output"}

Contexto enviado:
- rev_000294: "Nada a reclamar do sabor de pizza portuguesa. Não precisei esquentar pizza portuguesa. Veio numa embalagem bem resistente."
- rev_002980: "Me atenderam bem quando mandei mensagem. O gosto de pizza quatro queijos estava bem diferente do habitual."
- rev_002549: "O atendimento no chat foi bem ruim. Gostei de como embalaram pizza calabresa."
- rev_000673: "Resolvi experimentar pizza quatro queijos. Demoraram demais pra responder minha dúvida. Já estava morno quando abri. Espero que melhorem."
- rev_000650: "A embalagem veio bem fechada. Aqui em casa todo mundo gostou de pizza margherita."

## q09

Revisada: [ ]
Suporte factual: ______
Abstenção adequada: ______
Citações sustentam afirmações: ______
Observações: ______

Pergunta: Quais relatos sustentam reclamações de atraso do Burger do Zé nas últimas duas semanas até 01/11/2026?

Resposta bruta:
"EXATAMENTE [[Nao ha evidencia sobre reclamos de atraso do Burger do Zé na base de dados fornecida]]"

Erro: {"code": "invalid_citation", "type": "InvalidCitationError", "message": "Citation references a review outside the context", "invalid_ids": ["Nao ha evidencia sobre reclamos de atraso do Burger do Zé na base de dados fornecida"], "invalid_citation_count": 1}

Contexto enviado:
- rev_000212: "Ainda estava quentinho quando abri. Mais de uma hora esperando, muito além do combinado. Já pedi x-salada antes e dessa vez o sabor estava pior."

## q13

Revisada: [ ]
Suporte factual: ______
Abstenção adequada: ______
Citações sustentam afirmações: ______
Observações: ______

Pergunta: Quais relatos da Cantina Bella Massa mencionam espera excessiva de 19/10 a 01/11/2026?

Resposta bruta:
null

Erro: null

Contexto enviado:

## q22

Revisada: [ ]
Suporte factual: ______
Abstenção adequada: ______
Citações sustentam afirmações: ______
Observações: ______

Pergunta: Quem achou a refeição da Cantina Bella Massa desagradável ao paladar?

Resposta bruta:
"nhoque ao sugo encontrou sabor indesejado [rev_000300]\nlasanha bolonhesa chegou fria [rev_001760, rev_001051]\nravioli de queijo não gostou do sabor [rev_002684, rev_002234]\n\n[[SEM_EVIDENCIA]]\nNao ha review que achou a refeicao da Cantina Bella Massa desagradavel ao paladar apenas por causa do sabor, baseado nos dados fornecidos."

Erro: {"code": "generation_contract_error", "type": "GenerationContractError", "message": "Abstention marker must be the complete output"}

Contexto enviado:
- rev_000300: "Dessa vez acertaram no sabor de nhoque ao sugo. Pediria novamente."
- rev_001760: "Meu pedido foi lasanha bolonhesa. lasanha bolonhesa chegou frio. Gostei muito de lasanha bolonhesa."
- rev_001051: "lasanha bolonhesa não estava gostoso como das outras vezes. lasanha bolonhesa chegou frio. A embalagem veio bem fechada. Foram grossos quando entrei em contato."
- rev_002684: "Ja estava morno quando abri. ravioli de queijo nao estava gostoso como das outras vezes. Nao valeu a pena."
- rev_002234: "Chegou quente, deu pra comer na hora. Foram 92 minutos de espera, atrapalhou meu almoço. Esperava mais do sabor de ravióli de queijo."

## q25

Revisada: [ ]
Suporte factual: ______
Abstenção adequada: ______
Citações sustentam afirmações: ______
Observações: ______

Pergunta: Quais clientes do Burger do Zé relataram uma reação alérgica a amendoim?

Resposta bruta:
"EXATAMENTE [[Nenhuma revisão relatou reação alérgica a amendoim]]\n\nAs revisões apenas comentam sobre sabor, temperatura, atraso e embalagem. Nenhuma delas menciona reações alérgicas a amendoim."

Erro: {"code": "invalid_citation", "type": "InvalidCitationError", "message": "Citation references a review outside the context", "invalid_ids": ["Nenhuma revisão relatou reação alérgica a amendoim"], "invalid_citation_count": 1}

Contexto enviado:
- rev_002257: "Demoraram demais pra responder minha dúvida. O sabor de burger duplo estava muito bom."
- rev_002289: "Não gostei do sabor de x-bacon. Tive que esquentar x-bacon no micro-ondas. Fiquei esperando 112 min pelo pedido"
- rev_000799: "Não precisei esquentar burger duplo. burger duplo estava uma delícia, gostei até o fim. Pelo valor, achei uma boa compra."
- rev_002089: "Meu pedido foi batata frita grande. Pelo sabor, não pediria batata frita grande de novo."
- rev_001685: "Pedido feito e entregue em 33 min. Não gostei do sabor de batata frita grande."

## q26

Revisada: [ ]
Suporte factual: ______
Abstenção adequada: ______
Citações sustentam afirmações: ______
Observações: ______

Pergunta: Qual valor de reembolso via Pix foi recebido pelos clientes do Sushi Kaze?

Resposta bruta:
"EXATAMENTE, Nenhuma afirmação sustentada pelos dados fornecidos responde a pergunta sobre o valor de reembolso via Pix recebido pelos clientes do Sushi Kaze. [review_002759, review_001998, review_002142, review_001629, review_002675]"

Erro: {"code": "invalid_citation", "type": "InvalidCitationError", "message": "Citation references a review outside the context", "invalid_ids": ["review_002759, review_001998, review_002142, review_001629, review_002675"], "invalid_citation_count": 1}

Contexto enviado:
- rev_002759: "O valor coube no bolso. Dessa vez acertaram no sabor de hot roll. A embalagem protegeu bem hot roll. Recomendo esse lugar."
- rev_001998: "A entrega demorou demais, deu 76 minutos. combo 20 peças estava com um gosto ruim no final. Capricharam na embalagem de combo 20 peças. O preço de combo 20 peças estava bom."
- rev_002142: "Ainda estava quentinho quando abri. Gostei muito de yakisoba. Bom custo-beneficio nesse yakisoba. A entrega demorou demais, deu 115 minutos"
- rev_001629: "Meu pedido foi hot roll. O preço de hot roll estava bom. Veio frio, perdeu bastante a graça. hot roll estava uma delícia, gostei até o fim. A entrega foi rápida, uns 35 minutos."
- rev_002675: "Pedi combo 20 peças. O valor coube no bolso. O prazo passou e o pedido nada de chegar. Algumas coisas precisam melhorar."

## q27

Revisada: [ ]
Suporte factual: ______
Abstenção adequada: ______
Citações sustentam afirmações: ______
Observações: ______

Pergunta: Qual é a receita completa sem glúten da Marmita Fit Frango da Dona Rosa?

Resposta bruta:
"EXATAMENTE, Nenhuma afirmação sustentada pelos dados fornecidos em relação a receita completa sem glúten da Marmita Fit Frango da Dona Rosa. [review_001829, review_000400, review_00345, review_002438, review_002598]"

Erro: {"code": "invalid_citation", "type": "InvalidCitationError", "message": "Citation references a review outside the context", "invalid_ids": ["review_001829, review_000400, review_00345, review_002438, review_002598"], "invalid_citation_count": 1}

Contexto enviado:
- rev_001829: "o sabor de marmita fit frango valeu o pedido."
- rev_000400: "Chegou em 26 minutos, antes do previsto. Não gostei do sabor de marmita fit frango. marmita fit frango chegou bem quente."
- rev_000345: "O sabor de marmita executiva estava muito bom. Gostei de como embalaram marmita executiva. Em 20 min já estava aqui. Não achei caro pelo que veio. Veio frio, perdeu bastante a graça."
- rev_002438: "Falei com o restaurante e foram bem prestativos. Não precisei esquentar feijoada individual. Achei feijoada individual uma delícia."
- rev_002598: "Foi minha primeira compra aqui. O sabor de strogonoff estava muito bom. Tudo bem acomodado, sem embalagem aberta. O pedido levou só 25 minutos pra chegar. Falei com o restaurante e foram bem prestativos."

## q28

Revisada: [ ]
Suporte factual: ______
Abstenção adequada: ______
Citações sustentam afirmações: ______
Observações: ______

Pergunta: Quais consumidores da Doceria Ateliê Doce encontraram insetos na comida?

Resposta bruta:
"EXATAMENTE [[Não há evidencia sobre insetos na comida em nenhum dos reviews]]"

Erro: {"code": "invalid_citation", "type": "InvalidCitationError", "message": "Citation references a review outside the context", "invalid_ids": ["Não há evidencia sobre insetos na comida em nenhum dos reviews"], "invalid_citation_count": 1}

Contexto enviado:
- rev_002833: "Não achei o preço justo. A temperatura de brigadeiro gourmet estava adequada. Entregaram dentro do prazo. Dessa vez acertaram no sabor de brigadeiro gourmet. O pedido teve pontos bons e ruins."
- rev_002121: "cookie recheado veio abafado e quente demais. Não consegui terminar cookie recheado, o gosto não estava bom. Gostei de como embalaram cookie recheado."
- rev_002355: "Sobre torta de limão: Achei torta de limão uma delícia. Não fecharam direito a embalagem. Veio gelado e pronto pra consumir. Em 30 min já estava aqui."
- rev_000357: "Recebi agora meu pedido. Não precisei esperar muito, deu 18 min. O gosto de torta de limão me surpreendeu pra melhor. Demoraram demais pra responder minha dúvida."

## q29

Revisada: [ ]
Suporte factual: ______
Abstenção adequada: ______
Citações sustentam afirmações: ______
Observações: ______

Pergunta: Quais críticas de sabor recebeu a Pizza de Trufas da Pizzaria Forno Nobre?

Resposta bruta:
null

Erro: null

Contexto enviado:

## q30

Revisada: [ ]
Suporte factual: ______
Abstenção adequada: ______
Citações sustentam afirmações: ______
Observações: ______

Pergunta: Quais avaliações do Burger do Zé mencionam atrasos de 01/01 a 14/01/2030?

Resposta bruta:
null

Erro: null

Contexto enviado:

