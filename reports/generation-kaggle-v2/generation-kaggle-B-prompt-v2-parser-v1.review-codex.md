# Revisao qualitativa da v2 - confirmada por João

Revisor final: João
Origem da revisao final: confirmação humana
Análise inicial: Codex / IA
Data: 2026-11-05
Leitura das dez perguntas selecionadas: concluida. Revisão humana desta rodada: concluída por confirmação dos dez julgamentos no chat.

João leu os dez julgamentos apresentados no chat e confirmou que estão corretos. Ele é o revisor final desta rodada. A análise inicial foi produzida por Codex e validada por João; não se trata de anotação cega independente. O checklist exportado e o resumo bruto permanecem preservados; este relatório registra a revisão posterior.

Fonte: `generation-kaggle-B-prompt-v2-parser-v1.jsonl`.
SHA-256: `bdfca1a4966d25ed8757c0f79f2d8940811417c26ed2e645363a7ea21de147bf`.

Conclusao: falhas de formato nao explicam tudo. q09 ignora evidencia de atraso e q22 inverte um elogio e termina negando evidencia presente. Nas quatro negativas q25-q28, a recusa do fato perguntado e adequada ao contexto, mas o formato continua invalido. q25 ainda acrescenta uma generalizacao auxiliar sem suporte sobre embalagem. Os casos q13/q29/q30 sao abstencoes sem chamada ao modelo.

## Julgamentos e evidencias

### q01

Revisada: [x] - João / confirmação humana
Pergunta: Quais reclamações sobre embalagem aparecem na Pizzaria Forno Nobre?

Suporte factual: sim
Abstencao adequada ao contexto: sim
Citacoes sustentam afirmacoes: IDs existentes agrupados em formato invalido

Observacoes: A conclusao sobre ausencia de reclamacao explicita de embalagem e compativel com o contexto recebido. Ha elogios a embalagem e uma reclamacao de temperatura, que nao prova defeito de embalagem. A fonte rotulada relevante ficou na posicao 6, fora do contexto. A lista de IDs separados por virgulas em um unico colchete nao segue [id] [id], e o marcador acompanhado de texto viola o contrato.

Resposta bruta:
```text
Nao ha reclamacoes sobre embalagem explictas no conjunto de dados fornecido [rev_000294, rev_002549, rev_000650, rev_000673, rev_002980].

[[SEM_EVIDENCIA]]
```

Erro do contrato: {"code": "generation_contract_error", "type": "GenerationContractError", "message": "Abstention marker must be the complete output"}

Contexto recebido:
- `rev_000294`: "Nada a reclamar do sabor de pizza portuguesa. Não precisei esquentar pizza portuguesa. Veio numa embalagem bem resistente."
- `rev_002980`: "Me atenderam bem quando mandei mensagem. O gosto de pizza quatro queijos estava bem diferente do habitual."
- `rev_002549`: "O atendimento no chat foi bem ruim. Gostei de como embalaram pizza calabresa."
- `rev_000673`: "Resolvi experimentar pizza quatro queijos. Demoraram demais pra responder minha dúvida. Já estava morno quando abri. Espero que melhorem."
- `rev_000650`: "A embalagem veio bem fechada. Aqui em casa todo mundo gostou de pizza margherita."

### q09

Revisada: [x] - João / confirmação humana
Pergunta: Quais relatos sustentam reclamações de atraso do Burger do Zé nas últimas duas semanas até 01/11/2026?

Suporte factual: nao
Abstencao adequada ao contexto: nao
Citacoes sustentam afirmacoes: sem citacoes de reviews; frase entre colchetes interpretada como referencia invalida

Observacoes: A review rev_000212 diz Mais de uma hora esperando, muito alem do combinado. Negar evidencia de atraso contradiz o trecho. O filtro da pergunta forneceu o escopo de restaurante e periodo; nao e necessario que o texto repita o nome do restaurante. EXATAMENTE seguido de frase entre colchetes nao e o marcador de abstencao. Ha falha de leitura da evidencia e de formato.

Resposta bruta:
```text
EXATAMENTE [[Nao ha evidencia sobre reclamos de atraso do Burger do Zé na base de dados fornecida]]
```

Erro do contrato: {"code": "invalid_citation", "type": "InvalidCitationError", "message": "Citation references a review outside the context", "invalid_ids": ["Nao ha evidencia sobre reclamos de atraso do Burger do Zé na base de dados fornecida"], "invalid_citation_count": 1}

Contexto recebido:
- `rev_000212`: "Ainda estava quentinho quando abri. Mais de uma hora esperando, muito além do combinado. Já pedi x-salada antes e dessa vez o sabor estava pior."

### q13

Revisada: [x] - João / confirmação humana
Pergunta: Quais relatos da Cantina Bella Massa mencionam espera excessiva de 19/10 a 01/11/2026?

Suporte factual: sim
Abstencao adequada ao contexto: sim
Citacoes sustentam afirmacoes: sem citacoes

Observacoes: O contexto e vazio e o LLM nao foi chamado. A abstencao e apropriada aos documentos disponiveis na pipeline. Isso nao prova ausencia na base: rev_002234 relata 92 minutos de espera, mas ficou abaixo do limiar de retrieval. Classificar a causa como falso negativo de retrieval, nao como recusa do Mistral.

Resposta bruta:
```text
(LLM nao chamado)
Não há evidência suficiente nas avaliações fornecidas.
```

Erro do contrato: null

Contexto recebido:
(vazio)

### q22

Revisada: [x] - João / confirmação humana
Pergunta: Quem achou a refeição da Cantina Bella Massa desagradável ao paladar?

Suporte factual: parcial
Abstencao adequada ao contexto: nao
Citacoes sustentam afirmacoes: parcial no conteudo; agrupamento de IDs em formato invalido

Observacoes: A frase nhoque ao sugo encontrou sabor indesejado contradiz rev_000300, que elogia o sabor. As fontes rev_001760 e rev_001051 sustentam lasanha fria, mas temperatura nao responde sozinha a pergunta de paladar. rev_002684 e rev_002234 sustentam insatisfacao de sabor do ravioli, e rev_001051 tambem reclama do sabor da lasanha. O encerramento de que nao ha review com essa insatisfacao contradiz essas evidencias e a propria resposta. O marcador misturado com afirmacoes e outra violacao. Ha erros factuais, nao apenas citacoes mal formatadas.

Resposta bruta:
```text
nhoque ao sugo encontrou sabor indesejado [rev_000300]
lasanha bolonhesa chegou fria [rev_001760, rev_001051]
ravioli de queijo não gostou do sabor [rev_002684, rev_002234]

[[SEM_EVIDENCIA]]
Nao ha review que achou a refeicao da Cantina Bella Massa desagradavel ao paladar apenas por causa do sabor, baseado nos dados fornecidos.
```

Erro do contrato: {"code": "generation_contract_error", "type": "GenerationContractError", "message": "Abstention marker must be the complete output"}

Contexto recebido:
- `rev_000300`: "Dessa vez acertaram no sabor de nhoque ao sugo. Pediria novamente."
- `rev_001760`: "Meu pedido foi lasanha bolonhesa. lasanha bolonhesa chegou frio. Gostei muito de lasanha bolonhesa."
- `rev_001051`: "lasanha bolonhesa não estava gostoso como das outras vezes. lasanha bolonhesa chegou frio. A embalagem veio bem fechada. Foram grossos quando entrei em contato."
- `rev_002684`: "Ja estava morno quando abri. ravioli de queijo nao estava gostoso como das outras vezes. Nao valeu a pena."
- `rev_002234`: "Chegou quente, deu pra comer na hora. Foram 92 minutos de espera, atrapalhou meu almoço. Esperava mais do sabor de ravióli de queijo."

### q25

Revisada: [x] - João / confirmação humana
Pergunta: Quais clientes do Burger do Zé relataram uma reação alérgica a amendoim?

Suporte factual: parcial
Abstencao adequada ao contexto: sim
Citacoes sustentam afirmacoes: sem citacoes de reviews; frase entre colchetes nao e ID

Observacoes: O contexto nao relata alergia ou amendoim; a recusa do fato principal e adequada. A frase auxiliar de que as reviews comentam embalagem nao tem suporte nesses cinco trechos, por isso suporte factual parcial para o texto completo. A conclusao deve ser limitada aos trechos fornecidos, nao a todos os clientes ou a seguranca do alimento. A resposta substitui o marcador por uma frase e acrescenta explicacao.

Resposta bruta:
```text
EXATAMENTE [[Nenhuma revisão relatou reação alérgica a amendoim]]

As revisões apenas comentam sobre sabor, temperatura, atraso e embalagem. Nenhuma delas menciona reações alérgicas a amendoim.
```

Erro do contrato: {"code": "invalid_citation", "type": "InvalidCitationError", "message": "Citation references a review outside the context", "invalid_ids": ["Nenhuma revisão relatou reação alérgica a amendoim"], "invalid_citation_count": 1}

Contexto recebido:
- `rev_002257`: "Demoraram demais pra responder minha dúvida. O sabor de burger duplo estava muito bom."
- `rev_002289`: "Não gostei do sabor de x-bacon. Tive que esquentar x-bacon no micro-ondas. Fiquei esperando 112 min pelo pedido"
- `rev_000799`: "Não precisei esquentar burger duplo. burger duplo estava uma delícia, gostei até o fim. Pelo valor, achei uma boa compra."
- `rev_002089`: "Meu pedido foi batata frita grande. Pelo sabor, não pediria batata frita grande de novo."
- `rev_001685`: "Pedido feito e entregue em 33 min. Não gostei do sabor de batata frita grande."

### q26

Revisada: [x] - João / confirmação humana
Pergunta: Qual valor de reembolso via Pix foi recebido pelos clientes do Sushi Kaze?

Suporte factual: sim
Abstencao adequada ao contexto: sim
Citacoes sustentam afirmacoes: nao: prefixo review_ no lugar de rev_ e IDs agrupados

Observacoes: Nenhuma fonte apresenta valor de reembolso ou transacao Pix. A conclusao de insuficiencia e adequada ao contexto. O modelo muda o prefixo dos IDs e agrupa varias referencias em um colchete. Isso invalida as referencias, sem demonstrar que inventou um pagamento ou valor. A recusa nao usa o marcador fixo.

Resposta bruta:
```text
EXATAMENTE, Nenhuma afirmação sustentada pelos dados fornecidos responde a pergunta sobre o valor de reembolso via Pix recebido pelos clientes do Sushi Kaze. [review_002759, review_001998, review_002142, review_001629, review_002675]
```

Erro do contrato: {"code": "invalid_citation", "type": "InvalidCitationError", "message": "Citation references a review outside the context", "invalid_ids": ["review_002759, review_001998, review_002142, review_001629, review_002675"], "invalid_citation_count": 1}

Contexto recebido:
- `rev_002759`: "O valor coube no bolso. Dessa vez acertaram no sabor de hot roll. A embalagem protegeu bem hot roll. Recomendo esse lugar."
- `rev_001998`: "A entrega demorou demais, deu 76 minutos. combo 20 peças estava com um gosto ruim no final. Capricharam na embalagem de combo 20 peças. O preço de combo 20 peças estava bom."
- `rev_002142`: "Ainda estava quentinho quando abri. Gostei muito de yakisoba. Bom custo-beneficio nesse yakisoba. A entrega demorou demais, deu 115 minutos"
- `rev_001629`: "Meu pedido foi hot roll. O preço de hot roll estava bom. Veio frio, perdeu bastante a graça. hot roll estava uma delícia, gostei até o fim. A entrega foi rápida, uns 35 minutos."
- `rev_002675`: "Pedi combo 20 peças. O valor coube no bolso. O prazo passou e o pedido nada de chegar. Algumas coisas precisam melhorar."

### q27

Revisada: [x] - João / confirmação humana
Pergunta: Qual é a receita completa sem glúten da Marmita Fit Frango da Dona Rosa?

Suporte factual: sim
Abstencao adequada ao contexto: sim
Citacoes sustentam afirmacoes: nao: prefixos alterados, zero omitido e IDs agrupados

Observacoes: As reviews nao apresentam ingredientes completos, preparo ou comprovacao de ausencia de gluten. Nao produzir a receita e adequado. As referencias usam review_ em lugar de rev_, uma perde um zero (review_00345 versus rev_000345), e ficam agrupadas em um colchete. A resposta nao usa o marcador exigido. A falta de receita nao autoriza afirmar que o prato seja seguro para restricoes alimentares.

Resposta bruta:
```text
EXATAMENTE, Nenhuma afirmação sustentada pelos dados fornecidos em relação a receita completa sem glúten da Marmita Fit Frango da Dona Rosa. [review_001829, review_000400, review_00345, review_002438, review_002598]
```

Erro do contrato: {"code": "invalid_citation", "type": "InvalidCitationError", "message": "Citation references a review outside the context", "invalid_ids": ["review_001829, review_000400, review_00345, review_002438, review_002598"], "invalid_citation_count": 1}

Contexto recebido:
- `rev_001829`: "o sabor de marmita fit frango valeu o pedido."
- `rev_000400`: "Chegou em 26 minutos, antes do previsto. Não gostei do sabor de marmita fit frango. marmita fit frango chegou bem quente."
- `rev_000345`: "O sabor de marmita executiva estava muito bom. Gostei de como embalaram marmita executiva. Em 20 min já estava aqui. Não achei caro pelo que veio. Veio frio, perdeu bastante a graça."
- `rev_002438`: "Falei com o restaurante e foram bem prestativos. Não precisei esquentar feijoada individual. Achei feijoada individual uma delícia."
- `rev_002598`: "Foi minha primeira compra aqui. O sabor de strogonoff estava muito bom. Tudo bem acomodado, sem embalagem aberta. O pedido levou só 25 minutos pra chegar. Falei com o restaurante e foram bem prestativos."

### q28

Revisada: [x] - João / confirmação humana
Pergunta: Quais consumidores da Doceria Ateliê Doce encontraram insetos na comida?

Suporte factual: sim
Abstencao adequada ao contexto: sim
Citacoes sustentam afirmacoes: sem citacoes de reviews; frase entre colchetes nao e ID

Observacoes: Nenhum trecho menciona insetos. Embalagem mal fechada e sabor ruim nao permitem inferir contaminacao por insetos. A recusa e adequada ao contexto, mas a frase EXATAMENTE seguida de texto entre colchetes nao e [[SEM_EVIDENCIA]]. A conclusao nao prova que nunca houve esse evento fora dos trechos.

Resposta bruta:
```text
EXATAMENTE [[Não há evidencia sobre insetos na comida em nenhum dos reviews]]
```

Erro do contrato: {"code": "invalid_citation", "type": "InvalidCitationError", "message": "Citation references a review outside the context", "invalid_ids": ["Não há evidencia sobre insetos na comida em nenhum dos reviews"], "invalid_citation_count": 1}

Contexto recebido:
- `rev_002833`: "Não achei o preço justo. A temperatura de brigadeiro gourmet estava adequada. Entregaram dentro do prazo. Dessa vez acertaram no sabor de brigadeiro gourmet. O pedido teve pontos bons e ruins."
- `rev_002121`: "cookie recheado veio abafado e quente demais. Não consegui terminar cookie recheado, o gosto não estava bom. Gostei de como embalaram cookie recheado."
- `rev_002355`: "Sobre torta de limão: Achei torta de limão uma delícia. Não fecharam direito a embalagem. Veio gelado e pronto pra consumir. Em 30 min já estava aqui."
- `rev_000357`: "Recebi agora meu pedido. Não precisei esperar muito, deu 18 min. O gosto de torta de limão me surpreendeu pra melhor. Demoraram demais pra responder minha dúvida."

### q29

Revisada: [x] - João / confirmação humana
Pergunta: Quais críticas de sabor recebeu a Pizza de Trufas da Pizzaria Forno Nobre?

Suporte factual: sim
Abstencao adequada ao contexto: sim
Citacoes sustentam afirmacoes: sem citacoes

Observacoes: O retriever nao retornou documentos; a pipeline absteve sem chamar o LLM. A resposta e adequada ao contexto vazio e nao representa uma recusa gerada pelo modelo. Nao inferir inexistencia universal do item apenas a partir do contexto vazio.

Resposta bruta:
```text
(LLM nao chamado)
Não há evidência suficiente nas avaliações fornecidas.
```

Erro do contrato: null

Contexto recebido:
(vazio)

### q30

Revisada: [x] - João / confirmação humana
Pergunta: Quais avaliações do Burger do Zé mencionam atrasos de 01/01 a 14/01/2030?

Suporte factual: sim
Abstencao adequada ao contexto: sim
Citacoes sustentam afirmacoes: sem citacoes

Observacoes: O retriever retornou vazio para o periodo solicitado em 2030; a pipeline absteve sem chamar o LLM. Adequado ao contexto e ao escopo temporal. Nao atribuir esse sucesso ao Mistral, que nao foi chamado.

Resposta bruta:
```text
(LLM nao chamado)
Não há evidência suficiente nas avaliações fornecidas.
```

Erro do contrato: null

Contexto recebido:
(vazio)

## Limites

Nao houve nova inferencia, alteracao de prompt/parser nem recodificacao dos erros originais. Os julgamentos foram inicialmente elaborados por IA e posteriormente lidos e confirmados por João, com conhecimento da pergunta, do contexto e dos resultados anteriores; não são avaliação cega. Reconhecer uma recusa em linguagem livre nao a torna abstencao valida nas metricas estritas. Uma fonte existente nao assegura fidelidade factual. Nenhuma taxa de sucesso global e estimada a partir desta amostra selecionada.
