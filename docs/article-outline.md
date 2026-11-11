# PartnerCopilot: por que o extrator errou 16 de 19 textos sem aspecto

Em 19 textos de e-commerce sem aspecto aplicável, o extrator treinado só com reviews sintéticas de restaurantes acertou o mapa vazio em 3 casos. Regras simples acertaram 17. Nos 11 textos com rótulo, os dois métodos acertaram 6 mapas completos. O teste mede a transferência para e-commerce. O desempenho em reviews reais de restaurantes segue em aberto. [Avaliação externa B2W](absa-external-evaluation.md)

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

- Usar a ablação de ranking em 24 perguntas respondíveis já vistas. Sem filtro, a troca do MiniLM inglês pelo multilíngue teve delta de **−0,69 ponto percentual** em recall limitado@5, com **4 vitórias, 16 empates e 4 derrotas**. A hipótese de ganho com a troca ficou sem apoio nessa rodada.
- Com o mesmo embedding multilíngue, restringir ao restaurante levou o recall limitado@5 de **25,14% a 74,65%** e o hit@5 de **10/24 a 22/24**. A ablação usa só o filtro de restaurante e ranking sem corte de score.
- Interpretar o ganho como efeito do escopo explícito nas consultas deste benchmark. [Ablação completa](../reports/final-results-v1/RESULTADOS.md)

## 4. Geração: contrato de saída e fidelidade

- Usar as 27 saídas efetivamente geradas nas 30 perguntas antigas. A melhor variante de texto livre foi aceita em **2/27**. O retry acrescentou **25 chamadas** e recuperou **0/25**, mantendo **2/27**.
- A variante estruturada JSON v3 atingiu **14/27 aceitas pelo parser** nas perguntas antigas. Tratar a diferença como resultado entre versões já iteradas, com mudanças no prompt e no contrato.
- Contar o caso **n12**, da rodada posterior. O parser aceitou uma resposta com trecho literal, mas o elogio ao custo-benefício foi usado para sustentar uma afirmação sobre sabor. A mesma review descrevia gosto ruim no final. Separar aceitação estrutural de sustentação da afirmação.
- Usar a tabela de aceitação e a leitura assistida de n12 como fontes. [Relatório de geração](../reports/final-results-v1/RESULTADOS.md)

## 5. ABSA: de 0,98 no sintético a 9/30 em e-commerce real

- Nomear as métricas. No gold sintético, o QLoRA teve **macro-F1 de 0,9819** e **85/100 mapas exatos**. Na B2W, teve **9/30 mapas exatos**. Os dois números do título descrevem métricas diferentes.
- Relacionar a sobreposição de **70,4% das ocorrências de frases do gold** com o treino e a reprodução da convenção do gerador em **13/100 reviews** nas quais ela divergia do guia humano.
- O treino teve **0/1.263 exemplos sem aspecto aplicável**. Nos 11 textos reais com rótulo, QLoRA e regras empataram em **6/11**. Nos 19 vazios, o QLoRA acertou **3/19** e as regras **17/19**.
- No lote externo de 200, o QLoRA obteve **172/200 válidos pelo contrato estrito**, **199/200 sintaticamente válidos** e atribuiu sabor ou temperatura a **87/200**. A ausência de exemplos vazios é uma hipótese para a superprevisão, a ser testada em outra rodada.
- Fontes para resultados e limites. [Model card](absa-model-card.md) · [Avaliação externa B2W](absa-external-evaluation.md)

## 6. Filtro por aspecto: quatro braços no mesmo corpus

- Fixar o cenário no texto. **100 reviews sintéticas**, **24 perguntas respondíveis já vistas**, mesmo embedding e mesmos filtros de restaurante, item e data.
- Apresentar os relevantes no top 5 por braço. **37/120** sem aspecto, **45/120** com QLoRA, **45/120** com rótulos do gerador e **44/120** com rótulos humanos.
- O QLoRA passou no critério pré-registrado. Ganhou **6,67 pontos em precision@5** e **11,74 em recall limitado@5**, com **zero perguntas** perdendo evidência que já aparecia no top 5.
- O QLoRA e o gerador produziram rankings iguais. O empate descreve a filtragem neste corpus, em que os dois concordam em **98/100 mapas**. Em q22, o rótulo humano omite a polaridade de sabor por ambiguidade, e o braço humano deixa fora um relevante recuperado pelos outros dois braços com filtro.
- Usar a tabela e o protocolo como fontes. [Experimento em CPU](../reports/absa-retrieval-v1/README.md) · [Critério pré-registrado](decisions.md#comparação-e-critério-de-sucesso)

## 7. Limitações e trabalho futuro

- Delimitar o alcance. O retrieval foi avaliado em corpus sintético pequeno, com perguntas já vistas. A geração passou por iterações nas perguntas antigas. A B2W mede mudança para e-commerce, com 30 textos anotados por uma pessoa. O desempenho em avaliações reais de restaurantes segue em aberto.
- Propor uma v2 de treino com exemplos fora do domínio e exemplos sem aspecto aplicável. Reservar e anotar um novo teste antes do treino e manter os 30 textos anotados da B2W fora do treino.
- Comparar a v2 com as regras nos recortes com e sem rótulo. Acompanhar mapas exatos, previsões indevidas em referências vazias, validade estrita e efeito do filtro sobre evidência relevante.
