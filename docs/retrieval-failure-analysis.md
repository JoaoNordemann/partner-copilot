# Análise das cinco piores perguntas

Fonte: baseline operacional com filtros, k=8 e min_score=0,25. Não usamos o candidato
experimental 0,287, que não foi promovido ao default. Seleção determinística: perda
`1 - recall clássico@8` nas respondíveis; nas sem resposta, perda 1 se houver algum
documento retornado, senão 0. Ordenação por perda decrescente, MRR crescente (null=0)
e ID. Os cinco casos empatam em perda 1: q13, q25, q26, q27 e q28.

Li os três primeiros resultados de cada pergunta e a evidência relevante ausente quando
existe. Para q13, sem retorno operacional, li os candidatos antes do limiar. Esses
diagnósticos usam cosseno exato, separado dos scores operacionais do Chroma no JSON.
A revisão foi feita por IA, não por um anotador humano independente.

## q13 — ranking_semantico_fraco_e_corte_de_score

Quais relatos da Cantina Bella Massa mencionam espera excessiva de 19/10 a 01/11/2026?

- `rev_000407` (0.210): Paguei caro e esperava mais quantidade. Veio numa embalagem bem resistente
- `rev_002800` (0.194): Sobre nhoque ao sugo: O gosto de nhoque ao sugo estava bem diferente do habitual. Embalagem firme, nada ficou solto. Em 20 min já estava aqui. Algumas coisas precisam melhorar
- `rev_002234` (0.189): Chegou quente, deu pra comer na hora. Foram 92 minutos de espera, atrapalhou meu almoço. Esperava mais do sabor de ravióli de queijo.

A evidência explícita de 92 minutos está em terceiro antes do corte, com score 0,189. O primeiro fala de quantidade/preço e tem 0,210. Todos ficam abaixo de 0,25. Review mista dificulta ordenação, mas o trecho sobre demora não é ambíguo. Não é apenas um problema de filtro ou de limiar: reduzir o limiar também admitiria os distratores.

Próximo experimento: Avaliar reranking por relevância à pergunta e fusão lexical; não reduzir o corte global com base neste caso.

## q25 — falha_de_abstencao_semantica

Quais clientes do Burger do Zé relataram uma reação alérgica a amendoim?

- `rev_002257` (0.584): Demoraram demais pra responder minha dúvida. O sabor de burger duplo estava muito bom.
- `rev_002289` (0.424): Não gostei do sabor de x-bacon. Tive que esquentar x-bacon no micro-ondas. Fiquei esperando 112 min pelo pedido
- `rev_000799` (0.418): Não precisei esquentar burger duplo. burger duplo estava uma delícia, gostei até o fim. Pelo valor, achei uma boa compra.

O primeiro resultado critica atendimento e elogia burger, sem falar de amendoim ou reação alérgica. Similaridade temática de restaurante/comida não prova o evento pedido. Atribuição lexical específica ao nome do prato é hipótese, não causalidade demonstrada.

Próximo experimento: Exigir evidência explícita para a intenção e permitir abstenção após reranking; silêncio não prova segurança alimentar.

## q26 — falha_de_abstencao_e_confusao_de_intencao

Qual valor de reembolso via Pix foi recebido pelos clientes do Sushi Kaze?

- `rev_002759` (0.415): O valor coube no bolso. Dessa vez acertaram no sabor de hot roll. A embalagem protegeu bem hot roll. Recomendo esse lugar.
- `rev_001998` (0.394): A entrega demorou demais, deu 76 minutos. combo 20 peças estava com um gosto ruim no final. Capricharam na embalagem de combo 20 peças. O preço de combo 20 peças estava bom.
- `rev_002142` (0.383): Ainda estava quentinho quando abri. Gostei muito de yakisoba. Bom custo-beneficio nesse yakisoba. A entrega demorou demais, deu 115 minutos

O primeiro resultado diz que o valor coube no bolso; preço ou custo-benefício não informam reembolso nem Pix. Os seguintes também tratam de preço, sabor e atraso.

Próximo experimento: Distinguir avaliação de preço de transação de reembolso; testar reranking e detecção de suporte factual.

## q27 — falha_de_abstencao_e_entidade_sem_evidencia

Qual é a receita completa sem glúten da Marmita Fit Frango da Dona Rosa?

- `rev_001829` (0.515): o sabor de marmita fit frango valeu o pedido.
- `rev_000400` (0.403): Chegou em 26 minutos, antes do previsto. Não gostei do sabor de marmita fit frango. marmita fit frango chegou bem quente.
- `rev_000345` (0.384): O sabor de marmita executiva estava muito bom. Gostei de como embalaram marmita executiva. Em 20 min já estava aqui. Não achei caro pelo que veio. Veio frio, perdeu bastante a graça.

O primeiro resultado menciona exatamente marmita fit frango, mas só elogia sabor. Acerto da entidade não fornece receita nem lista de ingredientes. Filtrar também pelo item não criaria a informação ausente.

Próximo experimento: Separar perguntas de reviews de pedidos de receita/ingredientes; abster quando a fonte não oferece essa informação.

## q28 — falha_de_abstencao_semantica

Quais consumidores da Doceria Ateliê Doce encontraram insetos na comida?

- `rev_002833` (0.287): Não achei o preço justo. A temperatura de brigadeiro gourmet estava adequada. Entregaram dentro do prazo. Dessa vez acertaram no sabor de brigadeiro gourmet. O pedido teve pontos bons e ruins.
- `rev_002121` (0.264): cookie recheado veio abafado e quente demais. Não consegui terminar cookie recheado, o gosto não estava bom. Gostei de como embalaram cookie recheado.
- `rev_002355` (0.264): Sobre torta de limão: Achei torta de limão uma delícia. Não fecharam direito a embalagem. Veio gelado e pronto pra consumir. Em 30 min já estava aqui.

O primeiro resultado menciona preço, temperatura, prazo e sabor; o segundo critica gosto e calor. Nenhum relata insetos. Embalagem inadequada ou gosto ruim não autoriza inferir contaminação.

Próximo experimento: Validar a presença do evento solicitado; reranking ou busca híbrida são experimentos, sem garantia de resolver ausência de evidência.

## O que a leitura permite concluir

Os filtros de restaurante e período estão corretos nos casos inspecionados. A evidência
de q13 contém atraso explícito, mesmo em uma review mista. Nos quatro negativos não
há evidência do fato perguntado. Não encontramos erro de relevância que justificasse
alterar o gold ou tornar a métrica melhor. Isso não dispensa revisão humana posterior.

A causa dominante é falsa aceitação de evidência semanticamente próxima, mas insuficiente.
Não classificamos esses casos artificialmente como paráfrase fraca, filtro errado ou
relevância mal marcada. Em q13 há ranking fraco e efeito do limiar; em q25–q28 há falha
de abstenção, com confusão de intenção em q26 e acerto de entidade sem suporte em q27.
Nenhuma causa interna do embedding foi demonstrada experimentalmente: as explicações
são diagnósticos textuais e hipóteses para os próximos testes.

Para a entrevista: métricas agregadas localizaram os casos, mas ler as fontes mostrou
por que aumentar o limiar não basta. O sistema precisa distinguir tema semelhante de
evidência suficiente; reranking e busca híbrida devem ser medidos, não presumidos.

## Testes no CI

`tests/test_retriever.py` verifica filtros simples/combinados, datas inclusivas, item,
2*k candidatos, corte inclusivo por score, limite k, lista vazia e abstenção sem LLM.
`tests/test_retriever_dependencies.py` bloqueia explicitamente imports de Chroma, Torch,
Transformers e sentence-transformers em um processo novo. Os testes que abrem Chroma
foram movidos para `tests/test_retriever_integration.py`, preservando sua cobertura.

O workflow `.github/workflows/retriever-unit.yml` instala apenas pytest, Pydantic e
pydantic-settings; roda os dois arquivos unitários, sem instalar o pacote com extras
de modelos ou banco. A execução remota ainda depende do envio do commit.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_retriever.py tests/test_retriever_dependencies.py -v
```
