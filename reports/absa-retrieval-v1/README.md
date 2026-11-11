# Filtro ABSA no retrieval

Análise exploratória em 100 reviews sintéticas e 24 perguntas respondíveis já vistas.
Quatro coleções Chroma novas em base temporária usaram os mesmos vetores do MiniLM
multilíngue em CPU, com um documento por review. Todos os braços mantiveram
restaurante, item, período inclusivo, corte de 0,25 e busca de 2k candidatos.
Os seis controles negativos ficaram fora das médias.

O braço B passou no critério pré-registrado, com ganho de 6,67 pontos percentuais
em precision@5, ganho de 11,74 em recall limitado@5 e zero perguntas que perderam
toda a evidência antes presente no top 5.

| Braço | Acertos no top 5 | Precision@5 | Recall limitado@5 | Perguntas com acerto |
| --- | ---: | ---: | ---: | ---: |
| A · Sem aspecto | 37/120 | 30,83% | 73,12% | 22/24 |
| B · QLoRA | 45/120 | 37,50% | 84,86% | 23/24 |
| C · Gerador | 45/120 | 37,50% | 84,86% | 23/24 |
| D · Gold humano | 44/120 | 36,67% | 83,82% | 23/24 |

Cada célula mostra precision@5 e recall limitado@5 como frações.

| Pergunta | Aspecto | Relevantes | A | B | C | D |
| --- | --- | ---: | --- | --- | --- | --- |
| q01 | embalagem | 1 | 0/5 · 0/1 | 1/5 · 1/1 | 1/5 · 1/1 | 1/5 · 1/1 |
| q02 | atendimento | 1 | 1/5 · 1/1 | 1/5 · 1/1 | 1/5 · 1/1 | 1/5 · 1/1 |
| q03 | temperatura | 2 | 1/5 · 1/2 | 1/5 · 1/2 | 1/5 · 1/2 | 1/5 · 1/2 |
| q04 | sabor | 4 | 2/5 · 2/4 | 4/5 · 4/4 | 4/5 · 4/4 | 4/5 · 4/4 |
| q05 | embalagem | 3 | 1/5 · 1/3 | 1/5 · 1/3 | 1/5 · 1/3 | 1/5 · 1/3 |
| q06 | temperatura | 3 | 2/5 · 2/3 | 3/5 · 3/3 | 3/5 · 3/3 | 3/5 · 3/3 |
| q07 | sabor | 5 | 4/5 · 4/5 | 5/5 · 5/5 | 5/5 · 5/5 | 5/5 · 5/5 |
| q08 | preco | 3 | 1/5 · 1/3 | 1/5 · 1/3 | 1/5 · 1/3 | 1/5 · 1/3 |
| q09 | tempo_entrega | 1 | 1/5 · 1/1 | 1/5 · 1/1 | 1/5 · 1/1 | 1/5 · 1/1 |
| q10 | tempo_entrega | 1 | 1/5 · 1/1 | 1/5 · 1/1 | 1/5 · 1/1 | 1/5 · 1/1 |
| q11 | tempo_entrega | 1 | 1/5 · 1/1 | 1/5 · 1/1 | 1/5 · 1/1 | 1/5 · 1/1 |
| q12 | tempo_entrega | 1 | 1/5 · 1/1 | 1/5 · 1/1 | 1/5 · 1/1 | 1/5 · 1/1 |
| q13 | tempo_entrega | 1 | 0/5 · 0/1 | 0/5 · 0/1 | 0/5 · 0/1 | 0/5 · 0/1 |
| q14 | sabor | 2 | 2/5 · 2/2 | 2/5 · 2/2 | 2/5 · 2/2 | 2/5 · 2/2 |
| q15 | sabor | 2 | 2/5 · 2/2 | 2/5 · 2/2 | 2/5 · 2/2 | 2/5 · 2/2 |
| q16 | sabor | 1 | 1/5 · 1/1 | 1/5 · 1/1 | 1/5 · 1/1 | 1/5 · 1/1 |
| q17 | sabor | 2 | 2/5 · 2/2 | 2/5 · 2/2 | 2/5 · 2/2 | 2/5 · 2/2 |
| q18 | sabor | 2 | 2/5 · 2/2 | 2/5 · 2/2 | 2/5 · 2/2 | 2/5 · 2/2 |
| q19 | temperatura | 3 | 2/5 · 2/3 | 3/5 · 3/3 | 3/5 · 3/3 | 3/5 · 3/3 |
| q20 | tempo_entrega | 8 | 4/5 · 4/5 | 5/5 · 5/5 | 5/5 · 5/5 | 5/5 · 5/5 |
| q21 | embalagem | 5 | 1/5 · 1/5 | 1/5 · 1/5 | 1/5 · 1/5 | 1/5 · 1/5 |
| q22 | sabor | 4 | 3/5 · 3/4 | 4/5 · 4/4 | 4/5 · 4/4 | 3/5 · 3/4 |
| q23 | atendimento | 1 | 1/5 · 1/1 | 1/5 · 1/1 | 1/5 · 1/1 | 1/5 · 1/1 |
| q24 | preco | 1 | 1/5 · 1/1 | 1/5 · 1/1 | 1/5 · 1/1 | 1/5 · 1/1 |

O placar mostra vitórias, empates e derrotas da variante em relação à referência.

| Variante versus referência | Precision@5 | Recall limitado@5 |
| --- | ---: | ---: |
| B vs. A | 7 / 17 / 0 | 7 / 17 / 0 |
| C vs. A | 7 / 17 / 0 | 7 / 17 / 0 |
| D vs. A | 6 / 18 / 0 | 6 / 18 / 0 |
| C vs. B | 0 / 24 / 0 | 0 / 24 / 0 |
| D vs. B | 0 / 23 / 1 | 0 / 23 / 1 |
| D vs. C | 0 / 23 / 1 | 0 / 23 / 1 |

Nenhum braço perdeu um ID relevante que estava no top 5 de A. Antes do ranking,
D excluiu um relevante de q22, `rev_002800`. A review descreve um gosto diferente
do habitual, cuja polaridade ficou em aberto na anotação humana. O gerador e o
QLoRA marcam sabor negativo. A referência de retrieval considera a review
relevante. Ela estava fora do top 5 de A e entrou em B e C. q13 ficou sem
evidência nos quatro braços, embora seu relevante passasse pelos filtros.
O corte de 0,25 continuou valendo.

C é a referência idealizada para o efeito do filtro. B reproduziu o mapa do
gerador em 98/100 reviews e retornou os mesmos IDs na mesma ordem nas 30
perguntas, em k=5 e k=8. O custo observado dos erros de B frente a C foi zero
nessas consultas. Houve 0/100 saídas inválidas. O ganho descreve o efeito do
filtro no benchmark sintético. A diferença de q22 em D mostra a influência
da convenção de anotação.

O comportamento em reviews reais de restaurantes é desconhecido. Na B2W, o
QLoRA previu sabor ou temperatura em 87/200 textos de e-commerce e gerou
28/200 saídas fora do contrato. Essa confusão de domínio torna arriscado
depender de um filtro rígido em texto real sem avaliação no domínio.
[Avaliação externa](../../docs/absa-external-evaluation.md)

q29 e q30 retornaram vazio nos quatro braços. q25 a q28 retornaram candidatos
em todos os braços, com o filtro de aspecto desligado. Os IDs recuperados,
o diagnóstico em k=8 e os hashes de entrada constam em [results.json](results.json).

Para reproduzir com a revisão indicada do MiniLM no cache local, execute
`python scripts/evaluate_absa_retrieval.py --output CAMINHO_NOVO.json`
em um ambiente com o projeto instalado.
