# PartnerCopilot: por que o extrator errou 16 de 19 textos sem aspecto

No recorte de e-commerce sem aspecto aplicável (n = 19), o extrator treinado só com reviews sintéticas de restaurantes acertou o mapa vazio em 3 casos. Regras simples acertaram 17. Nos 11 textos com rótulo, os dois métodos acertaram 6 mapas completos. O teste mede a transferência para e-commerce. O desempenho em reviews reais de restaurantes segue em aberto. [Avaliação externa B2W](absa-external-evaluation.md)

## 1. O problema do parceiro

- Depois do resultado de abertura, apresentar uma pergunta operacional de um parceiro de restaurante, como investigar atrasos nas avaliações recentes de um item do cardápio.
- Explicar que o protótipo foi construído e treinado com avaliações sintéticas. O gerador permitiu reproduzir cenários e controlar os rótulos. A B2W entra como avaliação externa de e-commerce.
- Apresentar a proposta em uma frase. Buscar evidências no escopo do restaurante, responder com fontes e se abster quando faltar evidência.

## 2. Arquitetura e interfaces

- Desenhar o fluxo da ingestão ao Chroma e da API ao retrieval, à geração e à validação. O enriquecimento ABSA entra na ingestão como opt-in.
- Explicar por que usar `Protocol`. O pipeline depende do comportamento esperado de `VectorStore`, `Embedder`, `LLM` e `AspectExtractor`. Implementações reais e falsas podem cumprir esses contratos sem herdar de uma classe comum.
- Usar o extrator falso e o backend de predições congeladas como exemplos de testes em CPU. Mostrar onde a interface termina e onde o backend assume o carregamento do modelo ou a leitura do arquivo.
- Fonte do desenho e das decisões. [Decisões de arquitetura](decisions.md)

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
com NF4 na T4 aceitou **6/9** desse grupo e **13/27** do grupo contaminado.
[Resultados de geração](../reports/final-results-v1/RESULTADOS.md) ·
[Medição isolada na T4](../reports/mistral-t4-v1/README.md)

Em n12, o parser encontrou o ID correto e um trecho literal de
`rev_001172`. A review elogiava o custo-benefício e descrevia gosto ruim no
final. A resposta usou o elogio para dizer que o sabor era bom. A verificação
literal confirmou a origem do trecho, enquanto a leitura da review completa
expôs o erro na afirmação.
[Revisão do caso n12](../reports/generation-retrospective-v1/human-review.jsonl)

## 5. ABSA: de 0,98 no sintético a 9/30 em e-commerce real

- Nomear as métricas. No gold sintético, o QLoRA teve **macro-F1 de 0,9819** e **85/100 mapas exatos**. Na B2W, teve **9/30 mapas exatos**. Os dois números do título descrevem métricas diferentes.
- Relacionar a sobreposição de **70,4% das ocorrências de frases do gold** com o treino e a reprodução da convenção do gerador em **13/100 reviews** nas quais ela divergia do guia humano.
- O treino teve **0/1.263 exemplos sem aspecto aplicável**. Nos 11 textos reais com rótulo, QLoRA e regras empataram em **6/11**. Nos 19 vazios, o QLoRA acertou **3/19** e as regras **17/19**.
- No lote externo de 200, o QLoRA obteve **172/200 válidos pelo contrato estrito**, **199/200 sintaticamente válidos** e atribuiu sabor ou temperatura a **87/200**. A ausência de exemplos vazios é uma hipótese para a superprevisão, a ser testada em outra rodada.
- Fontes para resultados e limites. [Model card](absa-model-card.md) · [Avaliação externa B2W](absa-external-evaluation.md)

## 6. Filtro por aspecto: quatro braços no mesmo corpus

Mantive os mesmos embeddings e os mesmos filtros de restaurante, item e data
em quatro coleções Chroma novas. O teste usou 100 reviews sintéticas e 24
perguntas respondíveis já vistas. Todas pediam algum aspecto, inclusive as
seis formuladas como paráfrases.

| Braço | Relevantes no top 5 | Precision@5 | Recall limitado@5 | Vitórias / empates / derrotas vs. A |
| --- | ---: | ---: | ---: | ---: |
| A · Sem filtro de aspecto | 37/120 | 30,83% | 73,13% | — |
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

## 7. Limitações e trabalho futuro

- Delimitar o alcance. O retrieval foi avaliado em corpus sintético pequeno, com perguntas já vistas. A geração passou por iterações nas perguntas antigas. A B2W mede mudança para e-commerce, com 30 textos anotados por uma pessoa. O desempenho em avaliações reais de restaurantes segue em aberto.
- Propor uma v2 de treino com exemplos fora do domínio e exemplos sem aspecto aplicável. Reservar e anotar um novo teste antes do treino e manter os 30 textos anotados da B2W fora do treino.
- Comparar a v2 com as regras nos recortes com e sem rótulo. Acompanhar mapas exatos, previsões indevidas em referências vazias, validade estrita e efeito do filtro sobre evidência relevante.
