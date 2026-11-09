# Avaliação ABSA do checkpoint 253

Executada no Kaggle em uma Tesla T4, usando apenas a GPU 0. O modelo base foi carregado em NF4. O adapter foi
conferido pelo [manifesto](../../configs/absa-eval-v1.json). Cada método passou
uma vez pelos 100 IDs do gold humano e pelos 346 IDs dos templates reservados.
A sessão foi encerrada após cerca de 9 minutos, com o ZIP baixado e verificado.
[Notebook Kaggle](https://www.kaggle.com/code/jnordemann/partnercopilot-absa-avaliacao-v1/edit)

## Portão de validação

**140/140 saídas válidas, 0/140 inválidas**, dentro da tolerância de até 7.
Macro-F1 de desenvolvimento de **1,0000**. Todos os 12 pares tiveram precisão,
recall e F1 iguais a 1,0000. A validação compartilha 84,1% das ocorrências de
frases com o treino. O checkpoint foi escolhido pela menor perda teacher-forced
na primeira época, entre os três checkpoints avaliados. Pela regra dos três,
0/140 inválidos dá um limite superior unilateral aproximado de 2,1% a 95%,
sob a hipótese de observações independentes da mesma distribuição. Templates
repetidos restringem a leitura desse limite.

## Macro-F1 por conjunto

| Conjunto | Reviews | Pares com suporte | QLoRA | Qwen few-shot | Regras | TF-IDF + RL |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Gold humano | 100 | 12 | 0,9819 | 0,5162 | 0,4156 | 0,8688 |
| Gold sem ambiguidade | 96 | 12 | 0,9885 | 0,5233 | 0,4238 | 0,8717 |
| Templates reservados | 346 | 12 | 0,9948 | 0,5524 | 0,3198 | 0,7240 |
| Só famílias inéditas | 36 | 9 | 1,0000 | 0,4719 | 0,3333 | 0,3980 |
| Famílias mistas | 310 | 12 | 0,9946 | 0,5682 | 0,3194 | 0,7350 |

Todos os métodos produziram JSON válido em 100/100 no gold e em 346/346
nos templates reservados. O gold foi medido uma vez por método. O recorte
sem os quatro ambíguos foi [pré-registrado](../../docs/decisions.md#absa-protocolo-de-avaliação-pré-treino)
e reutiliza as mesmas previsões.

O Qwen base usou quatro demonstrações do treino, selecionadas por cobertura
de pares. O baseline usou a mesma instrução por review e a mesma decodificação
gulosa do QLoRA, precedidas pelas quatro demonstrações. A instrução e os exemplos
foram fixados antes de abrir os conjuntos finais. Essa comparação representa
essa configuração de few-shot. [Demonstrações](few-shot.json)

O QLoRA superou o few-shot nos dois conjuntos. O TF-IDF foi o baseline mais
forte e empatou com o QLoRA em 70/100 reviews do gold. A queda esperada do QLoRA
nos templates reservados não apareceu. O 1,0000 nas 36 reviews cobre apenas
9 dos 12 pares, pois os outros 3 não têm suporte nesse recorte. Os dados
reservados vêm do mesmo gerador
e os rótulos de referência são sintéticos. O gold compartilha 70,4% das
ocorrências de frases com o treino.

O conjunto completo de pares do QLoRA coincidiu com a referência em 85/100
reviews do gold, 340/346 dos templates reservados e 36/36 do recorte inédito.
Pela regra dos três, 0/36 erros de conjunto exato dá um limite superior
aproximado de 8,3% a 95%, sob as mesmas hipóteses. Os três pares ausentes do
recorte são excluídos do macro-F1. A avaliação sintética é quase determinística
para o extrator nessas amostras. Os 36 textos usam famílias reservadas com
rótulos do mesmo gerador. A avaliação de texto real está descrita no
[protocolo externo](../../docs/absa-external-evaluation.md).

## Divergências no gold

Revisão pós-avaliação dos 15 casos sem acerto exato. Classifiquei como
divergência de convenção quando o QLoRA reproduziu o rótulo sintético e o
guia humano fundamentava a omissão. Chamei de erro do extrator quando o par
adicional não tinha evidência textual e também estava ausente do rótulo
sintético. A leitura seguiu o guia congelado e encontrou **13 divergências
de convenção, 2 erros do extrator e 0 rótulos humanos questionáveis**.

A comparação direta dos rótulos do gerador com a referência humana nos
mesmos 100 IDs deu **87/100 conjuntos exatos**, **0,9855 de macro-F1**,
240 pares em comum, 13 extras do gerador e zero omissões. O gerador
atribuiu um par extra em cada uma das 13 reviews divergentes. A medida
quantifica a concordância da supervisão sintética com o guia humano
nesse recorte. Para o QLoRA, o mesmo gold deu 85/100 conjuntos exatos
e 0,9819 de macro-F1.

| Review | Classe | Par extra do QLoRA e motivo |
| --- | --- | --- |
| rev_001895 | Convenção | Sabor positivo a partir de aprovação geral do prato. |
| rev_001685 | Convenção | Entrega positiva a partir de 33 minutos sem julgamento. |
| rev_002363 | Convenção | Sabor positivo a partir de aprovação geral da torta. |
| rev_000613 | Convenção | Sabor positivo a partir de aprovação geral da vitamina. |
| rev_002476 | Convenção | Sabor positivo a partir de elogio geral ao prato. |
| rev_002800 | Convenção | Sabor negativo a partir de diferença do habitual sem avaliação explícita. |
| rev_002980 | Convenção | Sabor negativo a partir de diferença do habitual sem avaliação explícita. |
| rev_000708 | Convenção | Sabor positivo a partir de aprovação geral da linguiça. |
| rev_002257 | Erro do extrator | Entrega negativa a partir de demora para responder a uma dúvida. |
| rev_001760 | Convenção | Sabor positivo a partir de elogio geral à lasanha. |
| rev_002142 | Convenção | Sabor positivo a partir de elogio geral ao yakisoba. |
| rev_001916 | Convenção | Sabor positivo a partir de elogio geral à marmita. |
| rev_000650 | Convenção | Sabor positivo a partir de aprovação geral da pizza. |
| rev_000673 | Erro do extrator | Entrega negativa a partir de demora para responder a uma dúvida. |
| rev_000926 | Convenção | Entrega positiva a partir de 23 minutos sem julgamento. |

A única derrota para o TF-IDF foi em `rev_002800`. A review descreve o gosto
como diferente do habitual, elogia a embalagem e indica rapidez. O QLoRA
acertou embalagem e entrega e acrescentou sabor negativo, com F1 por review
de 0,80. O TF-IDF omitiu sabor e atingiu 1,00. O encerramento com crítica
genérica não liga explicitamente a insatisfação ao gosto.

As duas confusões de atendimento com prazo de entrega aparecem nos textos
sintéticos a seguir. Em ambos, a espera é por resposta a uma dúvida.

> **rev_002257** · Demoraram demais pra responder minha dúvida. O sabor de burger duplo estava muito bom.

> **rev_000673** · Resolvi experimentar pizza quatro queijos. Demoraram demais pra responder minha dúvida. Já estava morno quando abri. Espero que melhorem.

A mesma `rev_002800` foi considerada relevante para a pergunta q22 de
retrieval. No gold ABSA, a frase sobre um gosto diferente ficou sem
polaridade explícita. Na comparação por review, esse mesmo ponto gerou a
única derrota para o TF-IDF. A diferença mostra como a mesma frase pode
ser pertinente para uma busca e deixar a polaridade em aberto.
[Revisão de q22](../../docs/human-review-results.md#mudança-em-q22)

## Custo de execução

TF-IDF com seis regressões logísticas em um AMD Ryzen 5 5600, um thread,
Python 3.14.7 e scikit-learn 1.9.1. A medição após aquecimento inclui
vetorização, predição e serialização JSON, com os classificadores já ajustados.
As 100 predições coincidiram com as do scikit-learn 1.6.1 no Kaggle.

| Medição em CPU | Mediana | p95 |
| --- | ---: | ---: |
| Uma review por chamada, 100 chamadas | 1,29 ms | 1,44 ms |
| Lote de 100 reviews, 30 repetições | 4,71 ms | 5,22 ms |

O ajuste dos seis classificadores em 1.263 reviews levou 246 ms em uma execução.
O QLoRA foi avaliado em Tesla T4, com NF4 e lotes de até oito reviews. A sessão
de cerca de nove minutos incluiu preparação, carga do modelo, QLoRA, few-shot,
baselines clássicos e download. A rodada não registrou latência isolada do QLoRA.

## Placar por review

| Conjunto | QLoRA × Qwen few-shot | QLoRA × Regras | QLoRA × TF-IDF + RL |
| --- | ---: | ---: | ---: |
| Gold humano | 94 / 6 / 0 | 90 / 4 / 6 | 29 / 70 / 1 |
| Gold sem ambiguidade | 90 / 6 / 0 | 86 / 4 / 6 | 29 / 67 / 0 |
| Templates reservados | 334 / 11 / 1 | 320 / 26 / 0 | 244 / 102 / 0 |
| Só famílias inéditas | 29 / 7 / 0 | 20 / 16 / 0 | 14 / 22 / 0 |
| Famílias mistas | 305 / 4 / 1 | 300 / 10 / 0 | 230 / 80 / 0 |

Vitórias / empates / derrotas pelo F1 de pares exatos em cada review.

## Métricas por classe

Os JSONs preservam também os agregados por aspecto e polaridade. Um traço
indica métrica sem denominador. Pares sem suporte ficam fora do macro-F1.

### Validação

| Método | Par | Suporte | TP | FP | FN | Precisão | Recall | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| QLoRA | sabor=pos | 85 | 85 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | sabor=neg | 19 | 19 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | tempo_entrega=pos | 50 | 50 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | tempo_entrega=neg | 15 | 15 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | temperatura=pos | 48 | 48 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | temperatura=neg | 14 | 14 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | embalagem=pos | 32 | 32 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | embalagem=neg | 13 | 13 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | preco=pos | 23 | 23 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | preco=neg | 6 | 6 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | atendimento=pos | 13 | 13 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | atendimento=neg | 5 | 5 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |

### Gold humano

| Método | Par | Suporte | TP | FP | FN | Precisão | Recall | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| QLoRA | sabor=pos | 43 | 43 | 9 | 0 | 0,8269 | 1,0000 | 0,9053 |
| QLoRA | sabor=neg | 26 | 26 | 2 | 0 | 0,9286 | 1,0000 | 0,9630 |
| QLoRA | tempo_entrega=pos | 23 | 23 | 2 | 0 | 0,9200 | 1,0000 | 0,9583 |
| QLoRA | tempo_entrega=neg | 22 | 22 | 2 | 0 | 0,9167 | 1,0000 | 0,9565 |
| QLoRA | temperatura=pos | 26 | 26 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | temperatura=neg | 17 | 17 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | embalagem=pos | 26 | 26 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | embalagem=neg | 15 | 15 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | preco=pos | 23 | 23 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | preco=neg | 6 | 6 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | atendimento=pos | 7 | 7 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | atendimento=neg | 6 | 6 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| Qwen few-shot | sabor=pos | 43 | 43 | 13 | 0 | 0,7679 | 1,0000 | 0,8687 |
| Qwen few-shot | sabor=neg | 26 | 26 | 13 | 0 | 0,6667 | 1,0000 | 0,8000 |
| Qwen few-shot | tempo_entrega=pos | 23 | 23 | 10 | 0 | 0,6970 | 1,0000 | 0,8214 |
| Qwen few-shot | tempo_entrega=neg | 22 | 22 | 40 | 0 | 0,3548 | 1,0000 | 0,5238 |
| Qwen few-shot | temperatura=pos | 26 | 21 | 44 | 5 | 0,3231 | 0,8077 | 0,4615 |
| Qwen few-shot | temperatura=neg | 17 | 16 | 13 | 1 | 0,5517 | 0,9412 | 0,6957 |
| Qwen few-shot | embalagem=pos | 26 | 23 | 26 | 3 | 0,4694 | 0,8846 | 0,6133 |
| Qwen few-shot | embalagem=neg | 15 | 14 | 32 | 1 | 0,3043 | 0,9333 | 0,4590 |
| Qwen few-shot | preco=pos | 23 | 15 | 31 | 8 | 0,3261 | 0,6522 | 0,4348 |
| Qwen few-shot | preco=neg | 6 | 4 | 45 | 2 | 0,0816 | 0,6667 | 0,1455 |
| Qwen few-shot | atendimento=pos | 7 | 6 | 52 | 1 | 0,1034 | 0,8571 | 0,1846 |
| Qwen few-shot | atendimento=neg | 6 | 4 | 33 | 2 | 0,1081 | 0,6667 | 0,1860 |
| Regras | sabor=pos | 43 | 10 | 3 | 33 | 0,7692 | 0,2326 | 0,3571 |
| Regras | sabor=neg | 26 | 13 | 0 | 13 | 1,0000 | 0,5000 | 0,6667 |
| Regras | tempo_entrega=pos | 23 | 0 | 0 | 23 | 0,0000 | 0,0000 | 0,0000 |
| Regras | tempo_entrega=neg | 22 | 11 | 3 | 11 | 0,7857 | 0,5000 | 0,6111 |
| Regras | temperatura=pos | 26 | 7 | 0 | 19 | 1,0000 | 0,2692 | 0,4242 |
| Regras | temperatura=neg | 17 | 11 | 0 | 6 | 1,0000 | 0,6471 | 0,7857 |
| Regras | embalagem=pos | 26 | 6 | 0 | 20 | 1,0000 | 0,2308 | 0,3750 |
| Regras | embalagem=neg | 15 | 6 | 4 | 9 | 0,6000 | 0,4000 | 0,4800 |
| Regras | preco=pos | 23 | 6 | 3 | 17 | 0,6667 | 0,2609 | 0,3750 |
| Regras | preco=neg | 6 | 1 | 4 | 5 | 0,2000 | 0,1667 | 0,1818 |
| Regras | atendimento=pos | 7 | 2 | 0 | 5 | 1,0000 | 0,2857 | 0,4444 |
| Regras | atendimento=neg | 6 | 1 | 0 | 5 | 1,0000 | 0,1667 | 0,2857 |
| TF-IDF + RL | sabor=pos | 43 | 43 | 15 | 0 | 0,7414 | 1,0000 | 0,8515 |
| TF-IDF + RL | sabor=neg | 26 | 22 | 0 | 4 | 1,0000 | 0,8462 | 0,9167 |
| TF-IDF + RL | tempo_entrega=pos | 23 | 23 | 4 | 0 | 0,8519 | 1,0000 | 0,9200 |
| TF-IDF + RL | tempo_entrega=neg | 22 | 20 | 0 | 2 | 1,0000 | 0,9091 | 0,9524 |
| TF-IDF + RL | temperatura=pos | 26 | 24 | 0 | 2 | 1,0000 | 0,9231 | 0,9600 |
| TF-IDF + RL | temperatura=neg | 17 | 15 | 2 | 2 | 0,8824 | 0,8824 | 0,8824 |
| TF-IDF + RL | embalagem=pos | 26 | 21 | 0 | 5 | 1,0000 | 0,8077 | 0,8936 |
| TF-IDF + RL | embalagem=neg | 15 | 11 | 0 | 4 | 1,0000 | 0,7333 | 0,8462 |
| TF-IDF + RL | preco=pos | 23 | 20 | 3 | 3 | 0,8696 | 0,8696 | 0,8696 |
| TF-IDF + RL | preco=neg | 6 | 3 | 0 | 3 | 1,0000 | 0,5000 | 0,6667 |
| TF-IDF + RL | atendimento=pos | 7 | 7 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| TF-IDF + RL | atendimento=neg | 6 | 3 | 0 | 3 | 1,0000 | 0,5000 | 0,6667 |

### Gold sem ambiguidade

| Método | Par | Suporte | TP | FP | FN | Precisão | Recall | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| QLoRA | sabor=pos | 43 | 43 | 9 | 0 | 0,8269 | 1,0000 | 0,9053 |
| QLoRA | sabor=neg | 25 | 25 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | tempo_entrega=pos | 22 | 22 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | tempo_entrega=neg | 22 | 22 | 2 | 0 | 0,9167 | 1,0000 | 0,9565 |
| QLoRA | temperatura=pos | 25 | 25 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | temperatura=neg | 17 | 17 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | embalagem=pos | 25 | 25 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | embalagem=neg | 15 | 15 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | preco=pos | 23 | 23 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | preco=neg | 6 | 6 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | atendimento=pos | 6 | 6 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | atendimento=neg | 6 | 6 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| Qwen few-shot | sabor=pos | 43 | 43 | 12 | 0 | 0,7818 | 1,0000 | 0,8776 |
| Qwen few-shot | sabor=neg | 25 | 25 | 11 | 0 | 0,6944 | 1,0000 | 0,8197 |
| Qwen few-shot | tempo_entrega=pos | 22 | 22 | 8 | 0 | 0,7333 | 1,0000 | 0,8462 |
| Qwen few-shot | tempo_entrega=neg | 22 | 22 | 39 | 0 | 0,3607 | 1,0000 | 0,5301 |
| Qwen few-shot | temperatura=pos | 25 | 20 | 42 | 5 | 0,3226 | 0,8000 | 0,4598 |
| Qwen few-shot | temperatura=neg | 17 | 16 | 12 | 1 | 0,5714 | 0,9412 | 0,7111 |
| Qwen few-shot | embalagem=pos | 25 | 22 | 25 | 3 | 0,4681 | 0,8800 | 0,6111 |
| Qwen few-shot | embalagem=neg | 15 | 14 | 30 | 1 | 0,3182 | 0,9333 | 0,4746 |
| Qwen few-shot | preco=pos | 23 | 15 | 30 | 8 | 0,3333 | 0,6522 | 0,4412 |
| Qwen few-shot | preco=neg | 6 | 4 | 42 | 2 | 0,0870 | 0,6667 | 0,1538 |
| Qwen few-shot | atendimento=pos | 6 | 5 | 50 | 1 | 0,0909 | 0,8333 | 0,1639 |
| Qwen few-shot | atendimento=neg | 6 | 4 | 32 | 2 | 0,1111 | 0,6667 | 0,1905 |
| Regras | sabor=pos | 43 | 10 | 3 | 33 | 0,7692 | 0,2326 | 0,3571 |
| Regras | sabor=neg | 25 | 13 | 0 | 12 | 1,0000 | 0,5200 | 0,6842 |
| Regras | tempo_entrega=pos | 22 | 0 | 0 | 22 | 0,0000 | 0,0000 | 0,0000 |
| Regras | tempo_entrega=neg | 22 | 11 | 3 | 11 | 0,7857 | 0,5000 | 0,6111 |
| Regras | temperatura=pos | 25 | 7 | 0 | 18 | 1,0000 | 0,2800 | 0,4375 |
| Regras | temperatura=neg | 17 | 11 | 0 | 6 | 1,0000 | 0,6471 | 0,7857 |
| Regras | embalagem=pos | 25 | 6 | 0 | 19 | 1,0000 | 0,2400 | 0,3871 |
| Regras | embalagem=neg | 15 | 6 | 4 | 9 | 0,6000 | 0,4000 | 0,4800 |
| Regras | preco=pos | 23 | 6 | 3 | 17 | 0,6667 | 0,2609 | 0,3750 |
| Regras | preco=neg | 6 | 1 | 4 | 5 | 0,2000 | 0,1667 | 0,1818 |
| Regras | atendimento=pos | 6 | 2 | 0 | 4 | 1,0000 | 0,3333 | 0,5000 |
| Regras | atendimento=neg | 6 | 1 | 0 | 5 | 1,0000 | 0,1667 | 0,2857 |
| TF-IDF + RL | sabor=pos | 43 | 43 | 14 | 0 | 0,7544 | 1,0000 | 0,8600 |
| TF-IDF + RL | sabor=neg | 25 | 21 | 0 | 4 | 1,0000 | 0,8400 | 0,9130 |
| TF-IDF + RL | tempo_entrega=pos | 22 | 22 | 2 | 0 | 0,9167 | 1,0000 | 0,9565 |
| TF-IDF + RL | tempo_entrega=neg | 22 | 20 | 0 | 2 | 1,0000 | 0,9091 | 0,9524 |
| TF-IDF + RL | temperatura=pos | 25 | 23 | 0 | 2 | 1,0000 | 0,9200 | 0,9583 |
| TF-IDF + RL | temperatura=neg | 17 | 15 | 2 | 2 | 0,8824 | 0,8824 | 0,8824 |
| TF-IDF + RL | embalagem=pos | 25 | 20 | 0 | 5 | 1,0000 | 0,8000 | 0,8889 |
| TF-IDF + RL | embalagem=neg | 15 | 11 | 0 | 4 | 1,0000 | 0,7333 | 0,8462 |
| TF-IDF + RL | preco=pos | 23 | 20 | 3 | 3 | 0,8696 | 0,8696 | 0,8696 |
| TF-IDF + RL | preco=neg | 6 | 3 | 0 | 3 | 1,0000 | 0,5000 | 0,6667 |
| TF-IDF + RL | atendimento=pos | 6 | 6 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| TF-IDF + RL | atendimento=neg | 6 | 3 | 0 | 3 | 1,0000 | 0,5000 | 0,6667 |

### Templates reservados

| Método | Par | Suporte | TP | FP | FN | Precisão | Recall | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| QLoRA | sabor=pos | 215 | 215 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | sabor=neg | 55 | 55 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | tempo_entrega=pos | 163 | 163 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | tempo_entrega=neg | 64 | 64 | 3 | 0 | 0,9552 | 1,0000 | 0,9771 |
| QLoRA | temperatura=pos | 92 | 92 | 2 | 0 | 0,9787 | 1,0000 | 0,9892 |
| QLoRA | temperatura=neg | 48 | 46 | 0 | 2 | 1,0000 | 0,9583 | 0,9787 |
| QLoRA | embalagem=pos | 112 | 112 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | embalagem=neg | 50 | 50 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | preco=pos | 63 | 63 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | preco=neg | 15 | 15 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | atendimento=pos | 72 | 71 | 0 | 1 | 1,0000 | 0,9861 | 0,9930 |
| QLoRA | atendimento=neg | 13 | 13 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| Qwen few-shot | sabor=pos | 215 | 205 | 31 | 10 | 0,8686 | 0,9535 | 0,9091 |
| Qwen few-shot | sabor=neg | 55 | 50 | 48 | 5 | 0,5102 | 0,9091 | 0,6536 |
| Qwen few-shot | tempo_entrega=pos | 163 | 154 | 27 | 9 | 0,8508 | 0,9448 | 0,8953 |
| Qwen few-shot | tempo_entrega=neg | 64 | 64 | 95 | 0 | 0,4025 | 1,0000 | 0,5740 |
| Qwen few-shot | temperatura=pos | 92 | 78 | 187 | 14 | 0,2943 | 0,8478 | 0,4370 |
| Qwen few-shot | temperatura=neg | 48 | 36 | 33 | 12 | 0,5217 | 0,7500 | 0,6154 |
| Qwen few-shot | embalagem=pos | 112 | 108 | 108 | 4 | 0,5000 | 0,9643 | 0,6585 |
| Qwen few-shot | embalagem=neg | 50 | 50 | 64 | 0 | 0,4386 | 1,0000 | 0,6098 |
| Qwen few-shot | preco=pos | 63 | 58 | 133 | 5 | 0,3037 | 0,9206 | 0,4567 |
| Qwen few-shot | preco=neg | 15 | 15 | 122 | 0 | 0,1095 | 1,0000 | 0,1974 |
| Qwen few-shot | atendimento=pos | 72 | 70 | 185 | 2 | 0,2745 | 0,9722 | 0,4281 |
| Qwen few-shot | atendimento=neg | 13 | 9 | 71 | 4 | 0,1125 | 0,6923 | 0,1935 |
| Regras | sabor=pos | 215 | 90 | 5 | 125 | 0,9474 | 0,4186 | 0,5806 |
| Regras | sabor=neg | 55 | 12 | 1 | 43 | 0,9231 | 0,2182 | 0,3529 |
| Regras | tempo_entrega=pos | 163 | 0 | 0 | 163 | 0,0000 | 0,0000 | 0,0000 |
| Regras | tempo_entrega=neg | 64 | 13 | 6 | 51 | 0,6842 | 0,2031 | 0,3133 |
| Regras | temperatura=pos | 92 | 17 | 0 | 75 | 1,0000 | 0,1848 | 0,3119 |
| Regras | temperatura=neg | 48 | 32 | 0 | 16 | 1,0000 | 0,6667 | 0,8000 |
| Regras | embalagem=pos | 112 | 55 | 0 | 57 | 1,0000 | 0,4911 | 0,6587 |
| Regras | embalagem=neg | 50 | 9 | 1 | 41 | 0,9000 | 0,1800 | 0,3000 |
| Regras | preco=pos | 63 | 12 | 12 | 51 | 0,5000 | 0,1905 | 0,2759 |
| Regras | preco=neg | 15 | 0 | 1 | 15 | 0,0000 | 0,0000 | 0,0000 |
| Regras | atendimento=pos | 72 | 10 | 0 | 62 | 1,0000 | 0,1389 | 0,2439 |
| Regras | atendimento=neg | 13 | 0 | 0 | 13 | 0,0000 | 0,0000 | 0,0000 |
| TF-IDF + RL | sabor=pos | 215 | 209 | 8 | 6 | 0,9631 | 0,9721 | 0,9676 |
| TF-IDF + RL | sabor=neg | 55 | 33 | 0 | 22 | 1,0000 | 0,6000 | 0,7500 |
| TF-IDF + RL | tempo_entrega=pos | 163 | 109 | 30 | 54 | 0,7842 | 0,6687 | 0,7219 |
| TF-IDF + RL | tempo_entrega=neg | 64 | 33 | 0 | 31 | 1,0000 | 0,5156 | 0,6804 |
| TF-IDF + RL | temperatura=pos | 92 | 76 | 15 | 16 | 0,8352 | 0,8261 | 0,8306 |
| TF-IDF + RL | temperatura=neg | 48 | 40 | 0 | 8 | 1,0000 | 0,8333 | 0,9091 |
| TF-IDF + RL | embalagem=pos | 112 | 71 | 0 | 41 | 1,0000 | 0,6339 | 0,7760 |
| TF-IDF + RL | embalagem=neg | 50 | 35 | 0 | 15 | 1,0000 | 0,7000 | 0,8235 |
| TF-IDF + RL | preco=pos | 63 | 37 | 12 | 26 | 0,7551 | 0,5873 | 0,6607 |
| TF-IDF + RL | preco=neg | 15 | 2 | 1 | 13 | 0,6667 | 0,1333 | 0,2222 |
| TF-IDF + RL | atendimento=pos | 72 | 47 | 0 | 25 | 1,0000 | 0,6528 | 0,7899 |
| TF-IDF + RL | atendimento=neg | 13 | 5 | 0 | 8 | 1,0000 | 0,3846 | 0,5556 |

### Só famílias inéditas

| Método | Par | Suporte | TP | FP | FN | Precisão | Recall | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| QLoRA | sabor=pos | 15 | 15 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | sabor=neg | 3 | 3 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | tempo_entrega=pos | 8 | 8 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | tempo_entrega=neg | 5 | 5 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | temperatura=pos | 0 | 0 | 0 | 0 | — | — | — |
| QLoRA | temperatura=neg | 2 | 2 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | embalagem=pos | 1 | 1 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | embalagem=neg | 1 | 1 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | preco=pos | 2 | 2 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | preco=neg | 2 | 2 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | atendimento=pos | 0 | 0 | 0 | 0 | — | — | — |
| QLoRA | atendimento=neg | 0 | 0 | 0 | 0 | — | — | — |
| Qwen few-shot | sabor=pos | 15 | 15 | 5 | 0 | 0,7500 | 1,0000 | 0,8571 |
| Qwen few-shot | sabor=neg | 3 | 3 | 3 | 0 | 0,5000 | 1,0000 | 0,6667 |
| Qwen few-shot | tempo_entrega=pos | 8 | 8 | 5 | 0 | 0,6154 | 1,0000 | 0,7619 |
| Qwen few-shot | tempo_entrega=neg | 5 | 5 | 13 | 0 | 0,2778 | 1,0000 | 0,4348 |
| Qwen few-shot | temperatura=pos | 0 | 0 | 26 | 0 | 0,0000 | — | 0,0000 |
| Qwen few-shot | temperatura=neg | 2 | 2 | 1 | 0 | 0,6667 | 1,0000 | 0,8000 |
| Qwen few-shot | embalagem=pos | 1 | 1 | 17 | 0 | 0,0556 | 1,0000 | 0,1053 |
| Qwen few-shot | embalagem=neg | 1 | 1 | 11 | 0 | 0,0833 | 1,0000 | 0,1538 |
| Qwen few-shot | preco=pos | 2 | 2 | 18 | 0 | 0,1000 | 1,0000 | 0,1818 |
| Qwen few-shot | preco=neg | 2 | 2 | 10 | 0 | 0,1667 | 1,0000 | 0,2857 |
| Qwen few-shot | atendimento=pos | 0 | 0 | 23 | 0 | 0,0000 | — | 0,0000 |
| Qwen few-shot | atendimento=neg | 0 | 0 | 6 | 0 | 0,0000 | — | 0,0000 |
| Regras | sabor=pos | 15 | 15 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| Regras | sabor=neg | 3 | 0 | 0 | 3 | 0,0000 | 0,0000 | 0,0000 |
| Regras | tempo_entrega=pos | 8 | 0 | 0 | 8 | 0,0000 | 0,0000 | 0,0000 |
| Regras | tempo_entrega=neg | 5 | 0 | 0 | 5 | 0,0000 | 0,0000 | 0,0000 |
| Regras | temperatura=pos | 0 | 0 | 0 | 0 | — | — | — |
| Regras | temperatura=neg | 2 | 2 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| Regras | embalagem=pos | 1 | 1 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| Regras | embalagem=neg | 1 | 0 | 0 | 1 | 0,0000 | 0,0000 | 0,0000 |
| Regras | preco=pos | 2 | 0 | 2 | 2 | 0,0000 | 0,0000 | 0,0000 |
| Regras | preco=neg | 2 | 0 | 0 | 2 | 0,0000 | 0,0000 | 0,0000 |
| Regras | atendimento=pos | 0 | 0 | 0 | 0 | — | — | — |
| Regras | atendimento=neg | 0 | 0 | 0 | 0 | — | — | — |
| TF-IDF + RL | sabor=pos | 15 | 15 | 4 | 0 | 0,7895 | 1,0000 | 0,8824 |
| TF-IDF + RL | sabor=neg | 3 | 0 | 0 | 3 | 0,0000 | 0,0000 | 0,0000 |
| TF-IDF + RL | tempo_entrega=pos | 8 | 7 | 5 | 1 | 0,5833 | 0,8750 | 0,7000 |
| TF-IDF + RL | tempo_entrega=neg | 5 | 0 | 0 | 5 | 0,0000 | 0,0000 | 0,0000 |
| TF-IDF + RL | temperatura=pos | 0 | 0 | 1 | 0 | 0,0000 | — | 0,0000 |
| TF-IDF + RL | temperatura=neg | 2 | 2 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| TF-IDF + RL | embalagem=pos | 1 | 1 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| TF-IDF + RL | embalagem=neg | 1 | 0 | 0 | 1 | 0,0000 | 0,0000 | 0,0000 |
| TF-IDF + RL | preco=pos | 2 | 0 | 2 | 2 | 0,0000 | 0,0000 | 0,0000 |
| TF-IDF + RL | preco=neg | 2 | 0 | 0 | 2 | 0,0000 | 0,0000 | 0,0000 |
| TF-IDF + RL | atendimento=pos | 0 | 0 | 0 | 0 | — | — | — |
| TF-IDF + RL | atendimento=neg | 0 | 0 | 0 | 0 | — | — | — |

### Famílias mistas

| Método | Par | Suporte | TP | FP | FN | Precisão | Recall | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| QLoRA | sabor=pos | 200 | 200 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | sabor=neg | 52 | 52 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | tempo_entrega=pos | 155 | 155 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | tempo_entrega=neg | 59 | 59 | 3 | 0 | 0,9516 | 1,0000 | 0,9752 |
| QLoRA | temperatura=pos | 92 | 92 | 2 | 0 | 0,9787 | 1,0000 | 0,9892 |
| QLoRA | temperatura=neg | 46 | 44 | 0 | 2 | 1,0000 | 0,9565 | 0,9778 |
| QLoRA | embalagem=pos | 111 | 111 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | embalagem=neg | 49 | 49 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | preco=pos | 61 | 61 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | preco=neg | 13 | 13 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| QLoRA | atendimento=pos | 72 | 71 | 0 | 1 | 1,0000 | 0,9861 | 0,9930 |
| QLoRA | atendimento=neg | 13 | 13 | 0 | 0 | 1,0000 | 1,0000 | 1,0000 |
| Qwen few-shot | sabor=pos | 200 | 190 | 26 | 10 | 0,8796 | 0,9500 | 0,9135 |
| Qwen few-shot | sabor=neg | 52 | 47 | 45 | 5 | 0,5109 | 0,9038 | 0,6528 |
| Qwen few-shot | tempo_entrega=pos | 155 | 146 | 22 | 9 | 0,8690 | 0,9419 | 0,9040 |
| Qwen few-shot | tempo_entrega=neg | 59 | 59 | 82 | 0 | 0,4184 | 1,0000 | 0,5900 |
| Qwen few-shot | temperatura=pos | 92 | 78 | 161 | 14 | 0,3264 | 0,8478 | 0,4713 |
| Qwen few-shot | temperatura=neg | 46 | 34 | 32 | 12 | 0,5152 | 0,7391 | 0,6071 |
| Qwen few-shot | embalagem=pos | 111 | 107 | 91 | 4 | 0,5404 | 0,9640 | 0,6926 |
| Qwen few-shot | embalagem=neg | 49 | 49 | 53 | 0 | 0,4804 | 1,0000 | 0,6490 |
| Qwen few-shot | preco=pos | 61 | 56 | 115 | 5 | 0,3275 | 0,9180 | 0,4828 |
| Qwen few-shot | preco=neg | 13 | 13 | 112 | 0 | 0,1040 | 1,0000 | 0,1884 |
| Qwen few-shot | atendimento=pos | 72 | 70 | 162 | 2 | 0,3017 | 0,9722 | 0,4605 |
| Qwen few-shot | atendimento=neg | 13 | 9 | 65 | 4 | 0,1216 | 0,6923 | 0,2069 |
| Regras | sabor=pos | 200 | 75 | 5 | 125 | 0,9375 | 0,3750 | 0,5357 |
| Regras | sabor=neg | 52 | 12 | 1 | 40 | 0,9231 | 0,2308 | 0,3692 |
| Regras | tempo_entrega=pos | 155 | 0 | 0 | 155 | 0,0000 | 0,0000 | 0,0000 |
| Regras | tempo_entrega=neg | 59 | 13 | 6 | 46 | 0,6842 | 0,2203 | 0,3333 |
| Regras | temperatura=pos | 92 | 17 | 0 | 75 | 1,0000 | 0,1848 | 0,3119 |
| Regras | temperatura=neg | 46 | 30 | 0 | 16 | 1,0000 | 0,6522 | 0,7895 |
| Regras | embalagem=pos | 111 | 54 | 0 | 57 | 1,0000 | 0,4865 | 0,6545 |
| Regras | embalagem=neg | 49 | 9 | 1 | 40 | 0,9000 | 0,1837 | 0,3051 |
| Regras | preco=pos | 61 | 12 | 10 | 49 | 0,5455 | 0,1967 | 0,2892 |
| Regras | preco=neg | 13 | 0 | 1 | 13 | 0,0000 | 0,0000 | 0,0000 |
| Regras | atendimento=pos | 72 | 10 | 0 | 62 | 1,0000 | 0,1389 | 0,2439 |
| Regras | atendimento=neg | 13 | 0 | 0 | 13 | 0,0000 | 0,0000 | 0,0000 |
| TF-IDF + RL | sabor=pos | 200 | 194 | 4 | 6 | 0,9798 | 0,9700 | 0,9749 |
| TF-IDF + RL | sabor=neg | 52 | 33 | 0 | 19 | 1,0000 | 0,6346 | 0,7765 |
| TF-IDF + RL | tempo_entrega=pos | 155 | 102 | 25 | 53 | 0,8031 | 0,6581 | 0,7234 |
| TF-IDF + RL | tempo_entrega=neg | 59 | 33 | 0 | 26 | 1,0000 | 0,5593 | 0,7174 |
| TF-IDF + RL | temperatura=pos | 92 | 76 | 14 | 16 | 0,8444 | 0,8261 | 0,8352 |
| TF-IDF + RL | temperatura=neg | 46 | 38 | 0 | 8 | 1,0000 | 0,8261 | 0,9048 |
| TF-IDF + RL | embalagem=pos | 111 | 70 | 0 | 41 | 1,0000 | 0,6306 | 0,7735 |
| TF-IDF + RL | embalagem=neg | 49 | 35 | 0 | 14 | 1,0000 | 0,7143 | 0,8333 |
| TF-IDF + RL | preco=pos | 61 | 37 | 10 | 24 | 0,7872 | 0,6066 | 0,6852 |
| TF-IDF + RL | preco=neg | 13 | 2 | 1 | 11 | 0,6667 | 0,1538 | 0,2500 |
| TF-IDF + RL | atendimento=pos | 72 | 47 | 0 | 25 | 1,0000 | 0,6528 | 0,7899 |
| TF-IDF + RL | atendimento=neg | 13 | 5 | 0 | 8 | 1,0000 | 0,3846 | 0,5556 |

## Reprodução e artefatos

- [Protocolo executado](protocol.json) e [avaliador](../../scripts/evaluate_absa.py)
- [Métricas de validação](validation.json) e [métricas finais](final.json)
- [Demonstrações few-shot do treino](few-shot.json) e [ambiente do Kaggle](environment.json)
- O ZIP local contém as previsões JSONL e o log original. SHA-256
  `15d07e2a3037a749fc5103a0b46801882e6f750cc7113cae694ad99be8418ece`.
