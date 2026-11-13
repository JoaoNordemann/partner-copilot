# PartnerCopilot: por que o extrator errou 16 de 19 textos sem aspecto

Em avaliações reais de e-commerce sem nenhuma das categorias analisadas (n = 19), o extrator treinado só com avaliações sintéticas de restaurantes deixou a resposta vazia corretamente em **3 casos**. Regras simples acertaram **17**. As categorias avaliadas eram prazo de entrega, atendimento, preço e embalagem. Nos 11 textos com pelo menos uma dessas categorias anotada, ambos acertaram todos os rótulos em 6 casos. O teste mede a transferência para e-commerce. O desempenho em reviews reais de restaurantes segue em aberto. [Avaliação externa B2W](absa-external-evaluation.md)

## 1. O problema do parceiro

Quando um restaurante quer entender por que os pedidos chegam atrasados, precisa localizar relatos pertinentes entre avaliações sobre muitos assuntos. O PartnerCopilot busca avaliações no escopo do restaurante, gera respostas com fontes e se abstém quando falta evidência. O corpus do produto e o treino do extrator são sintéticos.

## 2. Arquitetura e processo

A ingestão valida as avaliações, gera embeddings e grava vetores e metadados no Chroma. A API recupera o contexto, chama o gerador e valida a saída. A extração de aspectos pode enriquecer os metadados na ingestão. Interfaces Python com `Protocol` permitem trocar os backends e testar o fluxo em CPU com implementações falsas.

Na revisão de relevância, a IA auxiliou na triagem e João confirmou os casos submetidos à revisão humana. O código foi escrito com assistência de IA e revisado pelo autor. [Decisões de arquitetura e avaliação](decisions.md)

## 3. Retrieval: o filtro de restaurante pesou mais que a troca de embedding

Nas 24 perguntas respondíveis da ablação, troquei o MiniLM inglês pelo
multilíngue e mantive o ranking sem filtro e sem corte de score. O recall
limitado@5 passou de **25,83% para 25,14%**, uma queda de **0,69 ponto
percentual**. O multilíngue ganhou em quatro perguntas, empatou em 16 e
perdeu em quatro. Nesta amostra, a troca de embedding trouxe pouca diferença.

Ao restringir o mesmo embedding multilíngue ao restaurante da pergunta,
o recall limitado@5 passou de **25,14% para 74,65%**. O número de perguntas
com pelo menos uma evidência relevante entre as cinco primeiras passou de
**10/24 para 22/24**. O filtro tira da disputa reviews de outros restaurantes
antes de ordená-las. Neste recorte, definir o escopo da busca teve mais efeito
que trocar o encoder.

O recall limitado divide os relevantes recuperados por quantos relevantes
cabem no top 5 de cada pergunta e depois tira a média. A ablação usou só o
filtro de restaurante, em um corpus sintético com perguntas já vistas.
[Ablação de retrieval](../reports/final-results-v1/RESULTADOS.md)

## 4. Geração: contrato de saída e fidelidade

Das 30 perguntas antigas, 27 chegaram ao gerador. A melhor variante em texto
livre passou no parser em **2/27**. Tentei recuperar as 25 rejeições com uma
segunda chamada por caso. Foram **0/25** recuperadas, e a aceitação ficou em
**2/27**. A versão v3, com JSON estruturado, chegou a **14/27** nas mesmas
perguntas. O prompt e o contrato mudaram juntos durante as iterações, de modo
que a comparação mede as versões completas. Na rodada originalmente limpa,
a v3 passou em **6/9**, incluindo duas abstenções geradas. A repetição isolada
com NF4 na T4 aceitou **6/9** desse grupo e **13/27** do grupo contaminado. Das 27 saídas
brutas contaminadas, 13 mudaram entre sessões. Só q19 mudou de decisão:
o trecho da terceira fonte deixou de corresponder à avaliação citada.
Seed, limite de tokens e versões principais coincidiram. A causa da
variação entre sessões ficou em aberto.

Nas 24 perguntas respondíveis do conjunto contaminado, havia ao menos
uma fonte rotulada relevante no contexto em **22/24** nas versões de
texto livre com até cinco documentos e **23/24** na v3 com até oito.
Na rodada de texto livre, q01 tinha evidência na sexta posição e q13
ficou sem evidência pelo limiar. A presença de uma fonte relevante
mede cobertura do contexto e não garante fidelidade da resposta.
[Resultados de geração](../reports/final-results-v1/RESULTADOS.md) ·
[Medição isolada na T4](../reports/mistral-t4-v1/README.md) · [Auditoria do contexto](../reports/generation-kaggle-D/semantic-refusal-audit.md)

Em n12, um caso da rodada originalmente limpa (n = 9 chamadas), o parser encontrou o ID correto e um trecho literal de
`rev_001172`. A review elogiava o custo-benefício e descrevia gosto ruim no
final. A resposta usou o elogio para dizer que o sabor era bom. A verificação
literal confirmou a origem do trecho, enquanto a leitura da review completa
expôs o erro na afirmação.
[Revisão do caso n12](../reports/generation-retrospective-v1/human-review.jsonl)

## 5. ABSA: do gold sintético ao e-commerce real

No gold sintético anotado por humanos (n = 100, avaliação final), o QLoRA atingiu **macro-F1 de 0,9819** e acertou **85/100 mapas completos**. Na B2W (n = 30 textos reais de e-commerce, teste externo com um anotador), acertou **9/30 mapas completos**. A comparação direta de acerto exato é 85/100 contra 9/30. No gold, **70,4% das ocorrências de frases** apareciam no treino, e em **13/100** avaliações o extrator reproduziu a convenção do gerador quando ela divergia do guia humano.

No lote externo (n = 200), **172/200** saídas passaram na validação estrita e **87/200** atribuíram sabor ou temperatura a textos de e-commerce. O treino sintético tinha **0/1.263** exemplos sem aspecto aplicável. A falta desses exemplos é uma hipótese para a superprevisão, e o teste combina mudança de domínio com mudança na origem dos textos. [Model card](absa-model-card.md) · [Avaliação externa B2W](absa-external-evaluation.md)

## 6. Filtro por aspecto: quatro braços no mesmo corpus

Mantive os mesmos embeddings e os mesmos filtros de restaurante, item e data
em quatro coleções Chroma novas. O teste usou 100 reviews sintéticas e 24
perguntas respondíveis já vistas. Todas pediam algum aspecto, inclusive as
seis formuladas como paráfrases.

| Braço | Relevantes no top 5 | Precision@5 | Recall limitado@5 | Vitórias / empates / derrotas vs. A |
| --- | ---: | ---: | ---: | ---: |
| A · Sem filtro de aspecto | 37/120 | 30,83% | 73,12% | — |
| B · Predições QLoRA | 45/120 | 37,50% | 84,86% | 7 / 17 / 0 |
| C · Rótulos do gerador | 45/120 | 37,50% | 84,86% | 7 / 17 / 0 |
| D · Rótulos humanos | 44/120 | 36,67% | 83,82% | 6 / 18 / 0 |

O filtro QLoRA passou no critério pré-registrado. Recuperou oito relevantes
a mais em 120 posições, com **+6,67 pontos em precision@5** e **+11,74 em
recall limitado@5**. Nenhuma pergunta perdeu toda a evidência que já aparecia
no top 5. O conjunto permite preencher **55/120 posições** com reviews
relevantes, de modo que os 45 acertos representam **81,82% do teto**.
Em cinco dos 17 empates, os rankings do top 5 ficaram idênticos. Nos outros
12, algum ID mudou sem alterar a contagem de relevantes.

O QLoRA e o gerador produziram rankings iguais. Os mapas completos
coincidiram em 98/100 reviews, e a convenção de aspecto negativo usada tanto
nos rótulos quanto na relevância favorece o filtro. O resultado mostra o efeito
da filtragem neste corpus e o teste deixou os dois métodos empatados. Em q22,
a anotação humana deixou em aberto a polaridade de um sabor descrito como
diferente do habitual. Essa review entrou com QLoRA e gerador, mas ficou fora
no braço humano. Houve 0/100 extrações inválidas no corpus sintético. Na
B2W foram 28/200, e a taxa em reviews reais de restaurantes segue desconhecida.
[Experimento em CPU](../reports/absa-retrieval-v1/README.md) ·
[Protocolo](decisions.md#comparação-e-critério-de-sucesso)

## 7. O que não funcionou

**O backend real devolveu HTTP 502 em 12 de 20 requisições.** Na T4 com NF4 e índice de 862 documentos, as 20 perguntas sequenciais eram respondíveis e já vistas. Houve **8 HTTP 200**, **7 rejeições de esquema**, **3 de trecho** e **2 de ID**. Os registros das falhas não guardam saída bruta nem tokens gerados, então truncamento ficou indeterminado. O índice e as perguntas diferem da avaliação isolada. O retry no experimento de texto livre também ficou em **0/25 recuperações** nas rejeições do conjunto contaminado. [Diagnóstico HTTP](../reports/mistral-t4-v1/README.md#diagnóstico-das-rejeições-http) · [Resultados de geração](../reports/final-results-v1/RESULTADOS.md)

### Custo na T4

| Conjunto | n por modo | NF4: tokens/s mediana e pico alocado | FP16: tokens/s mediana e pico alocado |
| --- | ---: | --- | --- |
| Originalmente limpo | 9 | 13,24 e 4,53 GiB | 9,23 e 14,16 GiB |
| Contaminado | 27 | 13,49 e 4,68 GiB | 9,33 e 14,32 GiB |

FP16 coube com o prompt v3, com **49 MiB livres** na menor leitura. A ordem fixa das cargas pode influenciar os tempos. A aceitação pelo parser favoreceu FP16 no grupo de 9 e NF4 no grupo de 27, com amostras pequenas e sem adjudicação factual pareada. [Benchmark na T4](../reports/mistral-t4-v1/README.md)

## 8. Limitações e trabalho futuro

**O desempenho em avaliações reais de restaurantes segue em aberto.** A busca foi medida em 24 perguntas já vistas sobre um corpus sintético. O filtro por aspecto compartilha a convenção do gerador com a relevância. Na geração, aceitação pelo parser e fidelidade são medidas distintas, como mostra n12. O teste externo anotado cobre 30 textos de e-commerce avaliados por um anotador.

Uma próxima avaliação deve reservar um novo conjunto anotado antes do treino e testar exemplos sem aspecto aplicável. Para o filtro, importa medir simultaneamente precisão e perda de evidência. Para o backend real, registrar tokens e motivo de parada em uma avaliação separada permitiria investigar as rejeições.
