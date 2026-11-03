# Avaliação de retrieval

## Artefatos

`data/eval/questions.jsonl` contém 30 perguntas com `id`, `pergunta`, `tipo`, `filtros`,
`relevantes`, `deve_abster` e um critério de julgamento legível. A composição é:
8 por restaurante/aspecto, 5 temporais, 5 por item, 6 paráfrases e 6 sem resposta.
Todos os oito restaurantes estão representados. Paráfrases evitam as expressões
literais que sinalizam o aspecto, mas podem compartilhar nomes próprios e palavras funcionais.

`corpus.jsonl` contém as 100 reviews do gold, com seus textos e rótulos anotados às cegas.
Somente metadados estruturais vêm dos dados brutos; descartamos os aspectos do gerador.
`relevance_audit.jsonl` registra a inspeção textual detalhada de dez perguntas, com
relevantes, controles negativos, primeiros resultados dos dois modos e decisões explicadas.
Os 100 textos foram lidos na preparação das perguntas; a revisão foi feita por IA,
não por um anotador humano independente. O manifesto informa essa limitação e os hashes.

## Isolamento e relevância

O gold está excluído do treino ABSA e do índice RAG de produção. Por isso a avaliação
cria uma collection **separada**, em banco temporário, somente com essas 100 reviews.
Não usamos os IDs gold como relevâncias contra o índice RAG de 862 reviews: seriam
impossíveis de recuperar e produziriam métricas inválidas. Os splits existentes não mudaram.

Relevante significa: evidência textual negativa do aspecto solicitado, dentro do
restaurante, item e período especificados. O guia de anotação decide casos ambíguos:
comida fria não implica atraso nem sabor ruim; elogio genérico não cria aspecto positivo;
reviews mistas continuam relevantes para a crítica explicitamente mencionada.
As listas de IDs estão congeladas no JSONL e não são calculadas a partir do resultado do modelo.

Os filtros **não contêm aspectos nem polaridades**, apenas restaurante, item ou datas.
Usar o mesmo rótulo como filtro e como resposta esperada tornaria a avaliação circular.
O filtro de item agora é exposto também pelo `Retriever` e pela `RAGPipeline`.
Quatro perguntas sem resposta têm documentos candidatos, mas nenhum oferece a evidência
pedida; as outras duas têm item inexistente ou janela vazia. Não tratamos silêncio sobre
alergênicos como prova de segurança, nem embalagem aberta como prova de contaminação.

O período recente é 19/10/2026 a 01/11/2026, inclusivo. O período anterior do Burger do Zé
é 05/10 a 18/10/2026. Não usamos `date.today()`. As perguntas temporais procuram evidências:
o gold pequeno não demonstra queda estatística de notas nem explica causas de uma tendência.

## Dois modos

- `sem_filtro`: busca somente por similaridade, sem `where`, com `2*k` candidatos,
  mesmo corte inclusivo por `min_score` e limite final de `k`.
- `com_filtro`: usa o retriever real, com os filtros estruturais explícitos da pergunta.

Ambos usam as mesmas perguntas, embeddings, relevâncias e corpus. O texto embutido é
somente a review. Assim, o primeiro modo também sofre com informações de restaurante,
item e data ausentes do texto; não é uma medida isolada da competência linguística do embedding.
O segundo modo mede este contrato do retriever, com filtros já fornecidos, não extração de
filtros a partir da pergunta, inferência do LLM ou o índice completo de produção.

Recall@k e MRR@k são médias macro das **24 perguntas respondíveis**. Abstenção correta e
falsa aceitação de evidência usam as **6 sem resposta**. Retornar qualquer documento numa
pergunta sem resposta conta como falsa aceitação de evidência pelo retriever, mesmo que um
LLM pudesse posteriormente se abster. O relatório inclui métricas por tipo e todos os IDs/scores.

## Baseline observado

MiniLM multilíngue, CPU, `k=8`, `min_score=0.25`, sem ajuste de limiar:

| Métrica | Sem filtro | Com filtro |
| --- | ---: | ---: |
| Recall@8 nas 24 respondíveis | 0,335 | 0,819 |
| MRR@8 nas 24 respondíveis | 0,263 | 0,682 |
| Abstenção correta nas 6 sem resposta | 0/6 | 2/6 |
| Falsa aceitação de evidência | 6/6 | 4/6 |
| Abstenção nas 24 respondíveis | 0/24 | 1/24 |

O relatório completo está em `reports/retrieval-baseline.json`, com versões do runtime,
revisão do modelo em cache e hashes do snapshot. O principal problema observado é a
abstenção semântica: as quatro perguntas sem evidência ainda passam pelo limiar.
Além disso, elogios ao aspecto consultado aparecem antes das críticas em vários casos.
A auditoria detalha esses erros, sem alterar relevâncias para acomodar os resultados.

Este conjunto é de **desenvolvimento/calibração**, com anotações de IA pendentes de revisão
humana. Se o limiar for ajustado nele, será necessário outro conjunto reservado para a
métrica final. Com apenas seis negativos, a taxa de abstenção muda em passos de 16,7 pontos;
não há suporte para conclusões de alta precisão estatística.

## Executar

Na raiz do repositório, valide os artefatos sem carregar modelos:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py --check-only
.\.venv\Scripts\python.exe -m pytest tests/test_eval_set.py -v
```

Com o modelo previamente disponível no cache local:

```powershell
$env:SENTENCE_TRANSFORMERS_HOME = "$PWD\work\hf-cache\sentence-transformers"
$env:HF_HUB_OFFLINE = '1'
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py --k 8 --min-score 0.25 --output work/evaluation/retrieval-run.json
Remove-Item Env:SENTENCE_TRANSFORMERS_HOME
Remove-Item Env:HF_HUB_OFFLINE
```

O script não baixa modelos. Para o cache padrão, omita `SENTENCE_TRANSFORMERS_HOME`.
`--eval-dir`, `--model`, `--k`, `--min-score` e `--output` permitem controlar a execução;
`DATA_EVAL_DIR` centraliza o diretório padrão. A saída deve ficar fora dos datasets e bancos.
As reviews são mantidas inteiras, uma por documento; o CLI rejeita textos que excedam a
janela do modelo para evitar truncamento silencioso. No Windows, o Chroma pode manter
handles até o processo encerrar; isso pode adiar a remoção do diretório temporário.

Comparação em k=1,3,5,8 com recall limitado, Hit, MRR e precision: [métricas e baselines](retrieval-baselines.md). O baseline anterior mantém sua definição original de recall clássico.
