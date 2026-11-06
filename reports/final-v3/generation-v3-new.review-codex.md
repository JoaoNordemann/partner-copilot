# Leitura das dez novas respostas V3

Revisor: Codex. Origem: IA. Leitura concluida; confirmacao humana pendente.

O checklist e o resumo exportados permanecem intactos. Esta leitura e posterior, separada, sem mudar prompt, parser ou metricas.

| ID | Aceita pelo parser | Trechos literais | Suporte factual por leitura | Pertinencia |
| --- | --- | --- | --- | --- |
| n11 | True | True | sim | sim |
| n12 | True | True | nao | nao |
| n13 | True | True | sim | sim |
| n14 | False | False | sim no conteudo principal | sim |
| n15 | False | False | parcial/contraditorio | parcial |
| n16 | False | False | parcial por combinar relatos diferentes | nao |
| n17 | True | True | sim | sim |
| n18 | None | None | sim diante do contexto vazio | sim |
| n19 | True | None | sim | sim |
| n20 | True | None | sim | sim |

## n11

Pergunta: Qual critica ao sabor de Pizza Portuguesa menciona gosto de produto velho?

A fonte rev_000797 afirma gosto de produto velho; o nucleo factual e pertinente. A resposta mistura portugues e ingles (tasted old), descumprindo a instrucao de idioma. O ponto apos o JSON foi ignorado.

Idioma: parcial

Resposta apresentada:
{"answer": "O produto tasted old. [rev_000797]", "sources": ["rev_000797"], "abstained": false, "abstention_reason": null, "metadata": {"latency_ms": 104537.179008, "retrieved_documents": 4, "context_documents": 4, "prompt_version": "partner-copilot-v3", "parser_version": "parser-v3", "llm_called": true, "generation": {"latency_ms": 7328.778184000043, "model_load_latency_ms": 97161.18049, "prompt_tokens": 854, "generated_tokens": 73, "max_new_tokens": 512, "context_window_tokens": 32768, "context_margin_tokens": 256, "seed": 42, "temperature": 0.0, "do_sample": false, "compute_dtype": "float16", "vram_baseline_allocated_bytes": {"cuda:0": 4130416640}, "vram_peak_allocated_bytes": {"cuda:0": 4560181760}, "vram_peak_reserved_bytes": {"cuda:0": 4613734400}}}}

Resposta bruta:
```text
{"abstem": false, "afirmacoes": [{"texto": "O produto tasted old.", "fontes": [{"review_id": "rev_000797", "trecho": "pizza portuguesa estava com gosto de produto velho."}]}]}.
```

Contexto:
- `rev_000797`: "O preço de pizza portuguesa estava bom. pizza portuguesa estava com gosto de produto velho. O lacre estava inteiro quando recebi."
- `rev_000294`: "Nada a reclamar do sabor de pizza portuguesa. Não precisei esquentar pizza portuguesa. Veio numa embalagem bem resistente."
- `rev_000604`: "Mais de uma hora esperando, muito além do combinado. Dessa vez acertaram no sabor de pizza portuguesa. A temperatura de pizza portuguesa estava ótima."
- `rev_002335`: "Pelo sabor, não pediria pizza portuguesa de novo. Paguei caro e esperava mais quantidade."

## n12

Pergunta: Como a review que elogia custo-beneficio da Linguica Artesanal descreve seu sabor?

A afirmacao diz sabor bom com base no custo-beneficio. A mesma review rev_001172 diz gosto ruim no final e bom custo-beneficio. O trecho e literal e o ID correto, mas a afirmacao troca o aspecto e contradiz a fonte sobre sabor. Exemplo claro de existencia de evidencia sem entailment.

Idioma: sim

Resposta apresentada:
{"answer": "O sabor da linguiça artesanal é descrito como bom no contexto do custo-benefício. [rev_001172]", "sources": ["rev_001172"], "abstained": false, "abstention_reason": null, "metadata": {"latency_ms": 6875.460521000036, "retrieved_documents": 4, "context_documents": 4, "prompt_version": "partner-copilot-v3", "parser_version": "parser-v3", "llm_called": true, "generation": {"latency_ms": 6458.4491820000385, "model_load_latency_ms": 97161.18049, "prompt_tokens": 874, "generated_tokens": 90, "max_new_tokens": 512, "context_window_tokens": 32768, "context_margin_tokens": 256, "seed": 42, "temperature": 0.0, "do_sample": false, "compute_dtype": "float16", "vram_baseline_allocated_bytes": {"cuda:0": 4138936320}, "vram_peak_allocated_bytes": {"cuda:0": 4572537856}, "vram_peak_reserved_bytes": {"cuda:0": 4712300544}}}}

Resposta bruta:
```text
{"abstem":false,"afirmacoes":[{"texto":"O sabor da linguiça artesanal é descrito como bom no contexto do custo-benefício.", "fontes":[{"review_id":"rev_001172", "trecho":"Bom custo-benefício nesse linguiça artesanal."}]}]}.
```

Contexto:
- `rev_001172`: "linguiça artesanal estava com um gosto ruim no final. Bom custo-benefício nesse linguiça artesanal."
- `rev_001286`: "Gostei bastante do sabor de linguiça artesanal."
- `rev_000351`: "Pedi pra dividir aqui em casa. linguiça artesanal esfriou antes de chegar aqui. Veio numa embalagem bem resistente. Já pedi linguiça artesanal antes e dessa vez o sabor estava pior."
- `rev_000708`: "Não achei caro pelo que veio. O lacre estava inteiro quando recebi. Aqui em casa todo mundo gostou de linguiça artesanal. Não precisei esquentar linguiça artesanal."

## n13

Pergunta: Que problema de lacre foi relatado no pedido de Costela no Bafo?

A fonte rev_001416 diz Veio sem lacre na sacola. A resposta atende ao problema de lacre; costelo e um erro de redacao do nome do prato, nao mudanca do fato principal.

Idioma: parcial

Resposta apresentada:
{"answer": "O costelo no bafo chegou sem lacre na sacola. [rev_001416]", "sources": ["rev_001416"], "abstained": false, "abstention_reason": null, "metadata": {"latency_ms": 5011.623136000026, "retrieved_documents": 1, "context_documents": 1, "prompt_version": "partner-copilot-v3", "parser_version": "parser-v3", "llm_called": true, "generation": {"latency_ms": 4956.9436649999825, "model_load_latency_ms": 97161.18049, "prompt_tokens": 536, "generated_tokens": 71, "max_new_tokens": 512, "context_window_tokens": 32768, "context_margin_tokens": 256, "seed": 42, "temperature": 0.0, "do_sample": false, "compute_dtype": "float16", "vram_baseline_allocated_bytes": {"cuda:0": 4138936320}, "vram_peak_allocated_bytes": {"cuda:0": 4396197888}, "vram_peak_reserved_bytes": {"cuda:0": 4712300544}}}}

Resposta bruta:
```text
{"abstem":false,"afirmacoes":[{"texto":"O costelo no bafo chegou sem lacre na sacola.", "fontes":[{"review_id":"rev_001416", "trecho":"Veio sem lacre na sacola."}]}]}.
```

Contexto:
- `rev_001416`: "Sobre costela no bafo: Veio sem lacre na sacola. Não precisei esquentar costela no bafo. Não consegui terminar costela no bafo, o gosto não estava bom."

## n14

Pergunta: Qual review de Pizza Portuguesa diz que o lacre estava inteiro, mas o sabor lembrava produto velho?

A review registra sabor de produto velho e lacre inteiro. O trecho proposto troca velho por velo e falha na regra literal. O conteudo principal tem apoio na review, mas a prova literal fornecida nao coincide com ela; o excerto de sabor tambem nao cobre sozinho o lacre. Resposta bloqueada, sem relaxamento retroativo.

Idioma: sim

Resposta apresentada:
null

Resposta bruta:
```text
{"abstem": false, "afirmacoes": [{"texto": "O lacre estava inteiro, mas o sabor lembrava produto velho.", "fontes": [{"review_id": "rev_000797", "trecho": "pizza portuguesa estava com gosto de produto velo."}]}]}.
```

Contexto:
- `rev_000797`: "O preço de pizza portuguesa estava bom. pizza portuguesa estava com gosto de produto velho. O lacre estava inteiro quando recebi."
- `rev_000604`: "Mais de uma hora esperando, muito além do combinado. Dessa vez acertaram no sabor de pizza portuguesa. A temperatura de pizza portuguesa estava ótima."
- `rev_000294`: "Nada a reclamar do sabor de pizza portuguesa. Não precisei esquentar pizza portuguesa. Veio numa embalagem bem resistente."
- `rev_002335`: "Pelo sabor, não pediria pizza portuguesa de novo. Paguei caro e esperava mais quantidade."

## n15

Pergunta: Que critica de preco aparece em Bolo de Pote mesmo numa avaliacao que elogia o sabor?

A afirmacao de preco alto cita rev_000445, cujo trecho diz Nao achei caro: contradicao de polaridade. O trecho Nao valeu a pena foi atribuido a rev_002127, onde nao existe; ele aparece em rev_002490. O bloco sobre preco injusto de rev_002176 tem apoio no texto completo, mas o trecho escolhido Nao pediria de novo nao prova sozinho o motivo. A regra literal bloqueou a atribuicao errada.

Idioma: sim

Resposta apresentada:
null

Resposta bruta:
```text
{"abstem":false,"afirmacoes":[{"texto":"O preço foi considerado alto por algumas pessoas que elogiaram o sabor de bolo de pote.", "fontes":[{"review_id":"rev_000445", "trecho":"Não achei caro pelo que veio."}, {"review_id":"rev_002127", "trecho":"Não valeu a pena"}]}, {"texto":"Outra pessoa também expressou que o preço não foi justificado por ela, apesar de gostar do sabor.", "fontes":[{"review_id":"rev_002176", "trecho":"Não pediria de novo."}]}]}]}.
```

Contexto:
- `rev_002127`: "A tampa veio solta, não gostei disso. O sabor de bolo de pote valeu o pedido. Chegou fresco e bem refrigerado. Dá pra melhorar."
- `rev_002485`: "Gostei bastante do sabor de bolo de pote. Entregaram dentro do prazo. A tampa veio solta, não gostei disso."
- `rev_002490`: "Sobre bolo de pote: Veio sem refrigeração, já estava morno. O sabor estava ótimo, pediria bolo de pote de novo. O preço subiu demais. Não valeu a pena"
- `rev_000445`: "Não achei caro pelo que veio. O sabor de bolo de pote estava muito bom. Entregaram dentro do prazo. Veio sem lacre na sacola."
- `rev_002176`: "bolo de pote veio com o sabor que eu esperava. Não achei o preço justo. Não pediria de novo."
- `rev_002787`: "Achei bolo de pote uma delícia. Falei com o restaurante e foram bem prestativos. Tudo bem acomodado, sem embalagem aberta. Pelo valor, achei uma boa compra. A temperatura de bolo de pote estava boa. Valeu a compra."

## n16

Pergunta: Qual relato de Temaki Salmao combina refrigeracao adequada, insatisfacao com gosto e espera alem da previsao?

A pergunta exige um relato com refrigeracao adequada, gosto ruim e demora. rev_000908 contem essa combinacao, mas a resposta combina refrigeracao inadequada de rev_001339 com gosto/demora de outra review. Um trecho acrescenta espaco final inexistente; outro muda o inicial para O e nao coincide literalmente. Bloqueio de transcricao e falha de alinhamento sao problemas separados.

Idioma: sim no texto principal; sufixo em ingles ignorado

Resposta apresentada:
null

Resposta bruta:
```text
{"abstem": false, "afirmacoes": [{"texto": "Não mantiveram temaki salmão refrigerado. O gosto não estava bom. Esperei quase duas horas e já tinha passado da previsão.", "fontes": [{"review_id": "rev_001339", "trecho": "Não mantiveram temaki salmão refrigerado. "}, {"review_id": "rev_000908", "trecho": "O gosto não estava bom. Esperei quase duas horas e já tinha passado da previsão."}]}]}.

Explanation:
The question asks for a report of Temaki Salmon that includes inadequate refrigeration, dissatisfaction with taste, and waiting time beyond the prediction. The provided JSONL data includes three reviews of Temaki Salmon from the same restaurant. Two of these reviews mention inadequate refrigeration and dissatisfaction with taste, while the third review mentions that the Temaki Salmon arrived at the correct temperature. Therefore, the following afirmation is valid: "Não mantiveram temaki salmão refrigerado. O gosto não estava bom. Esperei quase duas horas e já tinha passado da previsão." (They did not keep the Temaki Salmon refrigerated. The taste was not good. I waited almost two hours and it was past the prediction.)

The JSON output is:
{"abstem": false, "afirmacoes": [{"texto": "Não mantiveram temaki salmão refrigerado. O gosto não estava bom. Esperei quase duas horas e já tinha passado da previsão.", "fontes": [{"review_id": "rev_001339", "trecho": "Não mantiveram temaki salmão refrigerado."}, {"review_id": "rev_000908", "trecho": "O gosto não estava bom. Esperei quase duas horas e já tinha passado da previsão."}]}]}.
```

Contexto:
- `rev_001339`: "Achei temaki salmão uma delícia. Não mantiveram temaki salmão refrigerado."
- `rev_000908`: "Chegou fresco e bem refrigerado. Não consegui terminar temaki salmão, o gosto não estava bom. Esperei quase duas horas e já tinha passado da previsão. Não valeu a pena."
- `rev_002562`: "Veio bem gelado, na temperatura certa. O sabor estava ótimo, pediria temaki salmão de novo. A embalagem veio bem fechada. A entrega demorou demais, deu 112 minutos."

## n17

Pergunta: Como o cliente avaliou o atendimento da Feijoada Individual quando entrou em contato com a loja?

A review rev_002438 descreve o restaurante como prestativo quando o cliente entrou em contato. A resposta preserva a avaliacao positiva do atendimento.

Idioma: sim

Resposta apresentada:
{"answer": "O cliente avaliou o atendimento da Feijoada Individual positivamente, pois disse que foi bem atendido. [rev_002438]", "sources": ["rev_002438"], "abstained": false, "abstention_reason": null, "metadata": {"latency_ms": 6163.601591000088, "retrieved_documents": 1, "context_documents": 1, "prompt_version": "partner-copilot-v3", "parser_version": "parser-v3", "llm_called": true, "generation": {"latency_ms": 6106.246865999992, "model_load_latency_ms": 97161.18049, "prompt_tokens": 531, "generated_tokens": 87, "max_new_tokens": 512, "context_window_tokens": 32768, "context_margin_tokens": 256, "seed": 42, "temperature": 0.0, "do_sample": false, "compute_dtype": "float16", "vram_baseline_allocated_bytes": {"cuda:0": 4138936320}, "vram_peak_allocated_bytes": {"cuda:0": 4393183232}, "vram_peak_reserved_bytes": {"cuda:0": 5047844864}}}}

Resposta bruta:
```text
{"abstem":false,"afirmacoes":[{"texto":"O cliente avaliou o atendimento da Feijoada Individual positivamente, pois disse que foi bem atendido.", "fontes":[{"review_id":"rev_002438","trecho":"Falei com o restaurante e foram bem prestativos."}]}]}.
```

Contexto:
- `rev_002438`: "Falei com o restaurante e foram bem prestativos. Não precisei esquentar feijoada individual. Achei feijoada individual uma delícia."

## n18

Pergunta: Qual numero do protocolo oficial de fiscalizacao sanitaria foi citado para o Bolo de Pote?

Retrieval vazio: absteve sem chamar o modelo. Conta como acerto da pipeline, nao como uma terceira recusa gerada pelo Mistral.

Idioma: sim

Resposta apresentada:
{"answer": "Não há evidência suficiente nas avaliações fornecidas.", "sources": [], "abstained": true, "abstention_reason": "retriever_empty", "metadata": {"latency_ms": 54.45739599997523, "retrieved_documents": 0, "context_documents": 0, "prompt_version": "partner-copilot-v3", "parser_version": "parser-v3", "llm_called": false, "generation": null}}

Resposta bruta:
```text
(LLM nao chamado)
```

Contexto:
(vazio)

## n19

Pergunta: Qual concentracao de conservante, em mg/L, foi informada para a Vitamina de Morango?

As fontes de vitamina nao informam concentracao de conservante. O primeiro objeto marca abstem=true e afirmacoes vazias. A explicacao posterior em ingles foi ignorada na resposta e preservada no bruto.

Idioma: sim na resposta apresentada

Resposta apresentada:
{"answer": "Não há evidência suficiente nas avaliações fornecidas.", "sources": [], "abstained": true, "abstention_reason": "llm_insufficient_evidence", "metadata": {"latency_ms": 4900.207891000036, "retrieved_documents": 7, "context_documents": 7, "prompt_version": "partner-copilot-v3", "parser_version": "parser-v3", "llm_called": true, "generation": {"latency_ms": 4842.11304300004, "model_load_latency_ms": 97161.18049, "prompt_tokens": 1208, "generated_tokens": 44, "max_new_tokens": 512, "context_window_tokens": 32768, "context_margin_tokens": 256, "seed": 42, "temperature": 0.0, "do_sample": false, "compute_dtype": "float16", "vram_baseline_allocated_bytes": {"cuda:0": 4138936320}, "vram_peak_allocated_bytes": {"cuda:0": 4853885952}, "vram_peak_reserved_bytes": {"cuda:0": 5425332224}}}}

Resposta bruta:
```text
{"abstem":true,"afirmacoes":[]}.

The given data does not provide any information about the concentration of preservatives in the "Vitamina de Morango" product.
```

Contexto:
- `rev_000267`: "vitamina de morango nao estava gostoso como das outras vezes."
- `rev_002302`: "O sabor estava ótimo, pediria vitamina de morango de novo. A embalagem de vitamina de morango chegou aberta. No geral, foi razoável"
- `rev_002959`: "pedi vitamina de morango. não precisei esperar muito, deu 25 min. chegou fresco e bem refrigerado. vitamina de morango veio com um gosto estranho. a sacola estava lacrada e tudo no lugar."
- `rev_001190`: "O gosto de vitamina de morango me surpreendeu pra melhor. Fiquei esperando 104 min pelo pedido."
- `rev_000613`: "Aqui em casa todo mundo gostou de vitamina de morango. Não mantiveram vitamina de morango refrigerado. A entrega demorou demais, deu 71 minutos."
- `rev_001551`: "Gostei bastante do sabor de vitamina de morango."
- `rev_002693`: "Pedi pra dividir aqui em casa. A entrega foi rápida, uns 28 minutos. O sabor de vitamina de morango estava muito bom. A tampa veio solta, não gostei disso."

## n20

Pergunta: Qual marca de forno foi usada para assar a Pizza Portuguesa, segundo as reviews?

As reviews de pizza nao informam marca de forno. Abstem=true correto no primeiro objeto; explicacao em ingles posterior foi ignorada. Nao confundir essa abstencao correta com aderencia perfeita ao formato bruto.

Idioma: sim na resposta apresentada

Resposta apresentada:
{"answer": "Não há evidência suficiente nas avaliações fornecidas.", "sources": [], "abstained": true, "abstention_reason": "llm_insufficient_evidence", "metadata": {"latency_ms": 4917.3900749999575, "retrieved_documents": 4, "context_documents": 4, "prompt_version": "partner-copilot-v3", "parser_version": "parser-v3", "llm_called": true, "generation": {"latency_ms": 4868.156234999901, "model_load_latency_ms": 97161.18049, "prompt_tokens": 853, "generated_tokens": 55, "max_new_tokens": 512, "context_window_tokens": 32768, "context_margin_tokens": 256, "seed": 42, "temperature": 0.0, "do_sample": false, "compute_dtype": "float16", "vram_baseline_allocated_bytes": {"cuda:0": 4138936320}, "vram_peak_allocated_bytes": {"cuda:0": 4556914688}, "vram_peak_reserved_bytes": {"cuda:0": 5425332224}}}}

Resposta bruta:
```text
{"abstem":true,"afirmacoes":[]}.

The given data does not provide any evidence regarding the brand of the oven used to make the Portuguese Pizza, as the reviews only mention the taste, packaging, temperature, and waiting time.
```

Contexto:
- `rev_000294`: "Nada a reclamar do sabor de pizza portuguesa. Não precisei esquentar pizza portuguesa. Veio numa embalagem bem resistente."
- `rev_000604`: "Mais de uma hora esperando, muito além do combinado. Dessa vez acertaram no sabor de pizza portuguesa. A temperatura de pizza portuguesa estava ótima."
- `rev_000797`: "O preço de pizza portuguesa estava bom. pizza portuguesa estava com gosto de produto velho. O lacre estava inteiro quando recebi."
- `rev_002335`: "Pelo sabor, não pediria pizza portuguesa de novo. Paguei caro e esperava mais quantidade."

## Limites

Apenas quatro das sete respondiveis tiveram resposta substantiva aceita; n12, entre essas quatro, e semanticamente incorreta. n11, n13 e n17 tem nucleo factual sustentado, com falhas de idioma/redacao em n11/n13. Nao publicar isso como acuracia validada por humanos. As tres negativas foram corretamente abstidas pela pipeline, duas com LLM e uma sem LLM. Sao dez perguntas novas no mesmo corpus conhecido, com rotulos por IA. Nao ha inferencia causal contra os conjuntos anteriores.
