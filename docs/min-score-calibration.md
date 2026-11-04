# Calibração de min_score

O protocolo e a divisão 20/10 foram registrados antes da seleção, em `docs/decisions.md`
e `reports/min-score-protocol.json`. Mantivemos k=8 e os dados/relevâncias anteriores.
A grade fixa de 0 a 1, passo 0,001, maximiza balanced accuracy nas 20 perguntas de
calibração com filtros. Empates favorecem menos falsas aceitações e depois menor limiar.
Não houve seleção de outro limiar para o modo sem filtro.

## Resultado e trade-off

**Candidato experimental: 0,287**, comparado ao corte anterior 0,25.
Aceitação significa haver algum documento acima do corte; não significa resposta correta.
A coluna de evidência exige ao menos um ID relevante entre os oito que sobreviveram.

| Partição, com filtros | Limiar | Respondíveis aceitas | Respondíveis rejeitadas | Sem resposta rejeitadas | Sem resposta aceitas | Com evidência relevante |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Calibração | 0.250 | 15/16 | 1/16 | 1/4 | 3/4 | 15/16 |
| Calibração | 0.287 | 15/16 | 1/16 | 2/4 | 2/4 | 14/16 |
| Avaliação | 0.250 | 8/8 | 0/8 | 1/2 | 1/2 | 8/8 |
| Avaliação | 0.287 | 8/8 | 0/8 | 1/2 | 1/2 | 7/8 |

Na calibração, o aumento do limiar rejeita um negativo semântico adicional, mas também
elimina a última evidência relevante de uma pergunta ainda aceita. Na avaliação, não
aumenta a rejeição dos negativos e elimina a evidência relevante de outra pergunta.
Em conjunto, há evidência relevante em 21/24 respondíveis, contra 23/24 no corte antigo.
Esses totais descritivos não são uma nova otimização nas 30 perguntas.

Com o limiar escolhido, ainda são aceitos 2/3 negativos semânticos da calibração e
1/1 negativo semântico da avaliação. Os negativos estruturais, sem candidatos, sempre
são rejeitados e não demonstram capacidade de detectar ausência semântica de resposta.
O mesmo limiar no modo sem filtro rejeita 0/4 negativos na calibração e 0/2 na avaliação.
Não medimos alucinações de um LLM: são falsas aceitações de evidência pelo retriever.

## Distribuições do melhor score, com filtros

Casos sem candidato têm score `null`, não zero, e ficam fora dos quantis.

| Partição | Grupo | Perguntas | Sem candidato | Mínimo | Q1 | Mediana | Q3 | Máximo |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Calibração | Com resposta | 16 | 0 | 0.210 | 0.381 | 0.486 | 0.544 | 0.674 |
| Calibração | Sem resposta | 4 | 1 | 0.287 | 0.401 | 0.515 | 0.550 | 0.584 |
| Avaliação | Com resposta | 8 | 0 | 0.296 | 0.339 | 0.372 | 0.569 | 0.669 |
| Avaliação | Sem resposta | 2 | 1 | 0.415 | 0.415 | 0.415 | 0.415 | 0.415 |

Os scores se sobrepõem. Na calibração, os negativos com candidato vão de 0,287 a 0,584,
enquanto as respondíveis vão de 0,210 a 0,674. Na avaliação, o negativo semântico tem
score 0,415, maior que o de uma pergunta respondível com 0,296. Não existe limiar que
aceite essa positiva e rejeite esse negativo ao mesmo tempo. Um limiar acima de 0,584
rejeitaria os negativos semânticos observados com filtros, mas também muitas positivas;
isso é descrição posterior, não outro limiar escolhido.

## Melhor resultado por pergunta

O relatório JSON registra também o ID do primeiro resultado, sua relevância, o texto
da pergunta e os oito scores anteriores ao corte em cada modo.

| ID | Partição | Deve abster | Score com filtro | Score sem filtro |
| --- | --- | --- | ---: | ---: |
| q01 | calibration | não | 0.575579 | 0.575579 |
| q02 | evaluation | não | 0.564734 | 0.564734 |
| q03 | evaluation | não | 0.337235 | 0.375063 |
| q04 | calibration | não | 0.529064 | 0.636336 |
| q05 | calibration | não | 0.347553 | 0.347553 |
| q06 | calibration | não | 0.488459 | 0.533555 |
| q07 | calibration | não | 0.484006 | 0.512371 |
| q08 | evaluation | não | 0.350449 | 0.448180 |
| q09 | evaluation | não | 0.296366 | 0.428513 |
| q10 | calibration | não | 0.309319 | 0.367793 |
| q11 | calibration | não | 0.392076 | 0.455089 |
| q12 | evaluation | não | 0.394237 | 0.405754 |
| q13 | calibration | não | 0.209748 | 0.265041 |
| q14 | calibration | não | 0.674461 | 0.704664 |
| q15 | evaluation | não | 0.583289 | 0.723030 |
| q16 | calibration | não | 0.585453 | 0.585453 |
| q17 | calibration | não | 0.399824 | 0.399824 |
| q18 | evaluation | não | 0.668985 | 0.668985 |
| q19 | calibration | não | 0.672990 | 0.672990 |
| q20 | evaluation | não | 0.339512 | 0.381946 |
| q21 | calibration | não | 0.317500 | 0.422525 |
| q22 | calibration | não | 0.533313 | 0.533313 |
| q23 | calibration | não | 0.395580 | 0.451415 |
| q24 | calibration | não | 0.495629 | 0.495629 |
| q25 | calibration | sim | 0.584224 | 0.584224 |
| q26 | evaluation | sim | 0.414568 | 0.492743 |
| q27 | calibration | sim | 0.515212 | 0.542481 |
| q28 | calibration | sim | 0.286703 | 0.355327 |
| q29 | calibration | sim | sem candidato | 0.747955 |
| q30 | evaluation | sim | sem candidato | 0.456551 |

## Limitações e decisão operacional

As dez perguntas separadas não foram usadas nesta seleção, mas já eram conhecidas dos
baselines anteriores. Não são um teste final independente. Há só quatro negativos na
calibração e dois na avaliação; um único erro muda muito as taxas. As anotações de IA
ainda aguardam revisão humana. As distribuições do conjunto reservado foram descritas
apenas depois de congelar o limiar, sem usá-las para alterá-lo.

**Não promovemos 0,287 ao default global** nem alteramos `.env`: o ganho de rejeição não
se repetiu no conjunto separado e houve perda de evidência válida. `0,25` permanece o
default anterior, também inadequado para abstenção semântica; preservá-lo não é validá-lo.
O achado é que o melhor score do embedding sozinho não separa esses casos. Reranking
e busca híbrida são próximos experimentos, sem garantia de resolver ausência de resposta.
Antes de promoção, medir em perguntas novas e revisar as relevâncias independentemente.

## Reproduzir sem carregar modelos

```powershell
.\.venv\Scripts\python.exe scripts/calibrate_min_score.py --eval-dir data/eval --input reports/retrieval-comparison.json --protocol reports/min-score-protocol.json --output work/evaluation/min-score-run.json
.\.venv\Scripts\python.exe -m pytest tests/test_score_calibration.py -v
```

O cálculo reutiliza os rankings sem corte já registrados, com revisão do modelo e hashes
do mesmo corpus. O teste de isolamento altera os scores das dez perguntas de avaliação
e verifica que isso não muda o limiar selecionado ou a curva da calibração.

Os comandos desta reprodução histórica fixam v1 com `--eval-dir data/eval`. O padrão atual sem essa opção é `data/eval/human-v2`.
