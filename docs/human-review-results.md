# Resultado da revisão humana assistida

As 15 questões foram respondidas pelo responsável no chat, em 56 pares pergunta–review.
Essa contagem é de pares: uma review pode aparecer em mais de uma pergunta.
O responsável viu pools selecionados pela IA, recebeu explicações e já conhecia os
resultados anteriores. Portanto, esta é revisão humana assistida e parcial, não anotação
cega independente nem reinspeção exaustiva das 100 reviews ou das 30 perguntas.

## Decisões finais

| Questão | IDs selecionados | Resultado perante v1 |
| --- | --- | --- |
| q01 | `rev_001661` | Confirmação no pool apresentado |
| q02 | `rev_002257` | Confirmação no pool apresentado |
| q03 | `rev_001339`, `rev_001629` | Confirmação no pool apresentado |
| q04 | `rev_000400`, `rev_000934`, `rev_001212`, `rev_001552` | Confirmação no pool apresentado |
| q09 | `rev_000212` | Confirmação no pool apresentado |
| q10 | `rev_002237` | Confirmação no pool apresentado |
| q13 | `rev_002234` | Confirmação no pool apresentado |
| q14 | `rev_000813`, `rev_001076` | Confirmação no pool apresentado |
| q17 | `rev_000934`, `rev_001552` | Confirmação no pool apresentado |
| q19 | `rev_000673`, `rev_000813`, `rev_001661` | Confirmação no pool apresentado |
| q22 | `rev_001051`, `rev_002234`, `rev_002684`, `rev_002800` | Alteração |
| q25 | Nenhum dos candidatos apresentados | Confirmação no pool apresentado |
| q26 | Nenhum dos candidatos apresentados | Confirmação no pool apresentado |
| q27 | Nenhum dos candidatos apresentados | Confirmação no pool apresentado |
| q28 | Nenhum dos candidatos apresentados | Confirmação no pool apresentado |

## Mudança em q22

O responsável incluiu `rev_002800` entre os relevantes da pergunta sobre paladar
desagradável. O trecho diz que o gosto estava diferente do habitual. O guia ABSA
anterior considera essa formulação ambígua quando não há avaliação negativa explícita.
Registramos a escolha humana como exceção de relevância dessa pergunta, junto com a
divergência do guia; não a transformamos automaticamente em aspecto sabor negativo.
Os rótulos ABSA, o guia congelado, o corpus e os splits de treino/RAG não mudaram.

Em q09, o responsável removeu B após o esclarecimento de que a data estava fora da janela.
Em q19, passou de E para C/D/E após esclarecer o tratamento de frio/morno.
Em q01 e q03, as justificativas originais foram preservadas com ressalvas separadas:
o texto não comprova a causa do esfriamento nem o momento exato em que ele ocorreu.
O histórico de assistência e as dúvidas originais estão em human_review.jsonl.

## Versões e reprodução

- `data/eval/`: snapshot v1 preservado, com julgamentos originais de IA.
- `data/eval/human-v2/`: novas relevâncias e trilha da revisão; o corpus é idêntico ao v1.
- `reports/human-review-answers.json`: respostas e esclarecimentos do chat.
- `reports/human-v2/`: métricas operacionais, comparação multi-k e calibração recalculadas.
- `relevance_audit.jsonl` dentro de human-v2 preserva a auditoria histórica de IA;
  `human_review.jsonl` registra as decisões humanas que prevalecem nesta versão.

Os rankings e scores não foram recalculados porque os textos, filtros e modelo não mudaram.
O script verifica essa condição e a proveniência antes de reutilizá-los. Métricas
dependentes de relevância e as 200 repetições do baseline aleatório foram recalculadas.
O resultado não é uma melhoria do modelo: é a sensibilidade das métricas ao novo julgamento.

## Comparação principal: semântico com filtros, ranking sem corte

| k | Hit@k v1 → v2 | Recall limitado v1 → v2 | MRR v1 → v2 | Precision v1 → v2 |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0.5417 → 0.5417 | 0.5417 → 0.5417 | 0.5417 → 0.5417 | 0.5417 → 0.5417 |
| 3 | 0.8333 → 0.8333 | 0.6389 → 0.6389 | 0.6597 → 0.6597 | 0.3750 → 0.3750 |
| 5 | 0.9583 → 0.9583 | 0.8194 → 0.8090 | 0.6889 → 0.6889 | 0.3417 → 0.3417 |
| 8 | 1.0000 → 1.0000 | 0.9483 → 0.9483 | 0.6958 → 0.6958 | 0.2708 → 0.2760 |

No operacional com filtros, k=8 e min_score=0,25, o recall clássico continua 0,8191
e MRR 0,6819. Permanecem 4/6 negativas com documentos e 1/24 respondíveis com recall zero.
O limiar experimental escolhido nas mesmas 20 perguntas continua 0,287. A avaliação
nas dez separadas continua rejeitando 1/2 negativas e preservando evidência em 7/8
respondíveis. O default global permanece 0,25; esta revisão não valida sua promoção.
O corpus e as perguntas já eram conhecidos, portanto a versão revisada não é teste final.

## Executar

O default de DATA_EVAL_DIR aponta para data/eval/human-v2. Para reproduzir a avaliação
histórica, use --eval-dir data/eval explicitamente. O recálculo exige --parent-eval-dir
para não confundir a versão de origem com a versão revisada:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py --eval-dir data/eval/human-v2 --check-only
.\.venv\Scripts\python.exe scripts/rescore_reviewed_eval.py --parent-eval-dir data/eval --eval-dir data/eval/human-v2 --source-reports reports --output-dir work/evaluation/human-v2
.\.venv\Scripts\python.exe -m pytest tests/test_human_review.py -v
```

O recálculo reutiliza somente rankings registrados e não carrega modelos. Os testes
verificam a mudança exclusiva de q22, o corpus/ABSA intacto, a proveniência dos 56 pares,
a reprodução dos relatórios e a rejeição de scores de outro snapshot.
