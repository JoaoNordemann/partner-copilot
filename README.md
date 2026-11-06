# PartnerCopilot

RAG modular para análise de avaliações de restaurantes. Os dados gerados são
sintéticos e não representam dados reais do iFood.

## Ingestão

Execute a partir da raiz do projeto, em um ambiente Python compatível:

```powershell
python -m pip install -e ".[dev]"
python scripts/generate_synthetic_data.py --n 3000 --seed 42 --end-date 2026-11-01 --validate
python scripts/prepare_data_splits.py
python scripts/ingest.py --batch-size 128
python -m pytest
python -m ruff check .
```

Configure `.env` a partir de `.env.example`. A ingestão usa `DATA_RAW_DIR`,
`DATA_SPLITS_DIR`, `CHROMA_PATH`, `CHROMA_COLLECTION` e `EMBEDDING_MODEL`. O primeiro uso do embedding
precisa baixar o modelo multilingual; a ingestão não carrega o Mistral e não exige GPU.
`scripts/ingest.py` usa somente `data/splits/rag.jsonl` por padrão. Um `--input`
alternativo precisa corresponder ao split RAG registrado no manifesto.

O schema exige `category` e `bairro`, já emitidos pelo gerador. `created_at_int` é
calculado a partir de `created_at` como YYYYMMDD, evitando divergência entre datas.
Os aspectos são preservados na recuperação e também disponíveis em `aspect_<nome>`.
Aspectos não mencionados não possuem chave nos metadados. As decisões de data,
campos de filtro e polaridades estão em [docs/decisions.md](docs/decisions.md).

IDs das reviews são as chaves de upsert: repetir a mesma entrada atualiza os mesmos
registros. Não há remoção de documentos ausentes da entrada. IDs precisam ser únicos
no arquivo e na coleção, inclusive entre restaurantes. O gerador reinicia os IDs em
cada execução; arquivos independentes não devem ser combinados sem renomeá-los.
Uma falha pode deixar lotes anteriores gravados; corrija a entrada e execute novamente.
A contagem de processados representa linhas, não o número de novos documentos.

Índices antigos sem identificação do modelo de embedding devem ser reconstruídos
em outra coleção (`CHROMA_COLLECTION=reviews_v2`). O store rejeita modelo divergente
para evitar misturar vetores incompatíveis. Alterar o modelo exige uma nova coleção.

Filtros de exemplo para `ChromaStore.query`:

```python
where = {
    "$and": [
        {"restaurant_id": "rest_002"},
        {"category": "hamburguer"},
        {"created_at_int": {"$gte": 20261019}},
        {"created_at_int": {"$lte": 20261101}},
    ]
}
```

Os testes usam um embedding determinístico pequeno para verificar Chroma persistente
sem download de modelo. Isso não avalia a qualidade semântica do modelo multilingual.
A reprodução exata do gerador exige seed, data final e janela iguais.

## Auditoria dos dados sintéticos

```powershell
python scripts/audit_synthetic_data.py --end-date 2026-11-01 --output work/data-audit/current.json
```

A auditoria quantitativa e a leitura de exemplos estão em `docs/data-audit.md`.
Os textos respeitam o perfil térmico do item, mas continuam baseados em templates.
Para avaliar ABSA, use anotação humana independente e evite vazamento de duplicatas
ou famílias de templates entre treino e avaliação.

## Base externa para mudança de domínio

A amostra B2W-Reviews01 contém 200 textos reais de e-commerce, isolados em
`data/external/` para diagnóstico do extrator e inspeção de linguagem.
A licença da fonte original é **CC BY-NC-SA 4.0**; os textos não integram o índice RAG.
Origem, divergência de licença no espelho HF, amostragem e reprodução estão em
[docs/external-data.md](docs/external-data.md).

```powershell
python scripts/prepare_external_reviews.py --seed 42 --per-rating 40 --time-budget-minutes 10
```

## Referência para extração de aspectos

A amostra estratificada em `data/gold/` contém 100 reviews e anotações feitas por IA,
**pendentes de revisão humana independente**. A entrada cega expõe somente ID e texto.
O [guia de anotação](docs/annotation-guide.md) fixa dez regras; o
[protocolo e os limites do conjunto](docs/gold-set.md) registram seleção e proveniência.

```powershell
python scripts/prepare_gold_sample.py
python scripts/validate_gold_set.py
```

Reserve os IDs indicados no manifesto para fora do treino de ABSA. Não apresente as
anotações por IA como gold humano validado nem como evidência final de generalização.

## Separação entre avaliação, treino e RAG

O manifesto em `data/splits/manifest.json` registra IDs, hashes e contagens:
100 reviews para avaliação, 2.037 para `train_pool`, 862 para RAG e uma duplicata
do gold em quarentena. Não há sobreposição de IDs ou textos completos normalizados
entre os três conjuntos principais. O treino recebe apenas rótulos sintéticos do pool.

```powershell
python scripts/prepare_data_splits.py --check-only
```

O futuro treinador de ABSA deve carregar os dados com
`partner_copilot.data_splits.load_absa_train_pool`, que valida os splits antes de
retornar exemplos. A ingestão recusa o corpus integral e coleções antigas com IDs
fora do split RAG; nesse caso, escolha uma nova `CHROMA_COLLECTION` no ambiente.
As regras e os limites dessa separação estão em [decisions.md](decisions.md).

## Embeddings multilíngues

`SentenceTransformerEmbedder`, em `src/partner_copilot/ingestion/embedder.py`, expõe
`embed_documents` e `embed_query`, com carregamento lazy, batching e normalização L2.
O modelo vem de `EMBEDDING_MODEL`; `EMBEDDING_BATCH_SIZE`, `EMBEDDING_DEVICE` e
`EMBEDDING_PREFIX_MODE` controlam a inferência. E5 usa prefixos distintos para documentos
e consultas. Consulte [docs/embeddings.md](docs/embeddings.md) para exemplos e compatibilidade
entre coleções. A ingestão permanece limitada ao split RAG; dados públicos ficam separados.

## Store persistente

A classe `ChromaStore` está em `src/partner_copilot/ingestion/chroma_store.py`, com
`upsert`, `count`, `reset` e busca básica. O caminho vem de `CHROMA_PATH`; o nome
automático combina `CHROMA_COLLECTION` como prefixo, modelo e hash do contrato.
Metadados incluem cidade quando informada, sem inferir cidade a partir de bairro.
`reset()` remove somente documentos da collection alvo. API, filtros e persistência
estão descritos em [docs/chroma-store.md](docs/chroma-store.md).

## Pipeline de ingestão

`ingestion/pipeline.py` valida JSONL, ignora registros inválidos com log por linha e
retorna contagens de lidos, válidos, inseridos, atualizados e ignorados. IDs de origem
são preservadas; quando ausentes, são derivadas de hash determinístico. Reviews que
excedem o contexto do modelo são divididas por tokens, mantendo a ID de origem para citações.
A reexecução não duplica documentos e remove chunks obsoletos de reviews atualizadas.
A CLI continua limitada ao split RAG validado. Estratégia, limites e contadores estão em
[docs/ingestion.md](docs/ingestion.md).

## CLI de ingestão

```powershell
python scripts/ingest.py --input data/splits/rag.jsonl --db-path data/chroma --model paraphrase-multilingual-MiniLM-L12-v2 --batch-size 128
```

`--reset` limpa somente a collection selecionada antes de reingerir. A validação do split
e a preparação do modelo ocorrem antes de qualquer exclusão. Sem a flag, mantém-se o upsert.
O script apenas trata argumentos e delega ao serviço de ingestão. Precedência, reset e
códigos de saída estão em [docs/ingestion-cli.md](docs/ingestion-cli.md).

Configuração de paths, modelos e precedência: [guia de configuração](docs/configuration.md).

Execução dos testes e sanidade semântica: [guia de testes](docs/testing.md).

Perguntas, relevâncias e baseline de retrieval: [protocolo de avaliação](docs/retrieval-evaluation.md).

Métricas em quatro valores de k e comparação semântica/lexical/aleatória: [baselines de retrieval](docs/retrieval-baselines.md).

Calibração de abstenção: o melhor score do embedding apresenta sobreposição entre perguntas respondíveis e sem resposta. O candidato experimental 0,287 não melhorou a rejeição nas dez perguntas separadas e perdeu evidências válidas; não foi promovido ao default. Contagens, distribuições e limitações: [calibração de min_score](docs/min-score-calibration.md).

Análise das cinco piores perguntas: um falso negativo por ranking/corte e quatro falsas aceitações por falta de suporte factual. Filtros corretos não garantem relevância; tema parecido não basta. Evidências e testes unitários de CI: [análise de falhas](docs/retrieval-failure-analysis.md).

## Limite do score como detector de evidência

Com k=8 e min_score=0,25, 4/6 perguntas sem resposta retornaram documentos e
1/24 respondíveis teve recall@8 zero. Esses cinco casos são todas as perdas máximas
observadas com filtros. A evidência correta de atraso de q13 pontua 0,189, enquanto
os melhores candidatos sem resposta de q25 e q27 pontuam 0,584 e 0,515. Nenhum limiar
único aceita aquela evidência e rejeita ambos os negativos. O filtro restringe o
domínio, mas não recalibra o cosseno: similaridade temática não certifica suporte factual.

Tabelas completas, distribuições, origem das relevâncias e CI remoto verificado estão
em [revisão de resultados](docs/retrieval-checkpoint.md). A inspeção de IA está marcada;
a [revisão humana independente](docs/human-review-checklist.md) continua pendente.

## Revisão humana dos julgamentos

O responsável concluiu no chat a revisão assistida de 15 perguntas, em 56 pares
pergunta–review. Uma decisão alterou a avaliação: rev_002800 foi incluída em q22.
A exceção de relevância não altera os rótulos ABSA e continua registrada como divergência
do guia anterior. Os snapshots históricos foram preservados; a revisão não foi cega
nem exaustiva. Novos julgamentos, proveniência e métricas estão em
[resultado da revisão humana](docs/human-review-results.md).

Baselines sem embeddings: no corpus revisado com filtros, o aleatório já atinge Hit@8 de 93,1% e palavras-chave 95,8%, contra 100% semântico. O ganho de ordenação deve ser avaliado em Hit@1/MRR/precision. [Resultados e comando sem modelo](docs/cheap-baselines-check.md).

## Versão padrão da avaliação

`DATA_EVAL_DIR=data/eval/human-v2` é o padrão do config e do `.env.example`.
Os comandos de avaliação sem `--eval-dir` usam os julgamentos revisados.
Para reproduzir resultados históricos do v1, informe `--eval-dir data/eval`.
Um valor explícito de `DATA_EVAL_DIR` no ambiente ou `.env` prevalece sobre o default;
se ainda estiver em `data/eval`, atualize-o para `data/eval/human-v2`.
No recálculo de relatórios, informe `--parent-eval-dir data/eval` para identificar a origem.

Prompt ativo partner-copilot-v1: exige evidência explícita, citações por afirmação e abstenção padronizada. Reviews são delimitadas como dados; ações só com evidência. A pipeline usa até cinco documentos e registra metadados. [Contrato, versionamento e limites dos testes](docs/prompt-design.md).

Geração reutilizável e instrumentada: provider lazy por processo, seed por chamada, temperatura padrão zero, margem de tokens e metadados de latência/VRAM por GPU. [Como funciona e como medir](docs/generation-runtime.md).

CLI de consulta:

```powershell
.\.venv\Scripts\partner-copilot.exe ask "Quais reclamações de entrega aparecem?" --restaurant-id rest_002 --json
```

Mostra resposta, fontes e metadados. Citação fora do contexto rejeita a resposta com
código invalid_citation e contagem de referências inválidas.
[Uso, filtros e códigos de saída](docs/ask-cli.md).

Testes sem GPU: a pipeline usa doubles e confirma que lista vazia não chama o LLM, que o prompt leva IDs/instruções e que citações inválidas e abstenção são detectáveis. Teste real marcado gpu só roda com --run-gpu e pesos em cache; fica fora do CI. [Comandos e escopo](docs/testing.md).


### Versoes independentes de geracao

PROMPT_VERSION e PARSER_VERSION sao selecionados separadamente; os defaults
continuam partner-copilot-v1 e parser-v1. v2 foi criada depois de ver a v1 nas
mesmas 30 perguntas: os resultados futuros nesse conjunto sao de desenvolvimento,
nao uma avaliacao independente. Nenhuma rodada v2 foi executada nesta alteracao.

- partner-copilot-v2: prompt mais curto, idioma explicito, exemplo inventado e
  formato de saida ao final. Usa o mesmo contexto JSONL escapado.
- parser-v2: apenas normaliza `\_` para `_`, depois aplica o contrato estrito v1.
  Nao aceita marcador acompanhado de texto, IDs ausentes ou linhas sem citacao.

Selecione as quatro combinacoes em arquivos separados. Exemplo para medir apenas
mudanca de prompt, mantendo o parser original:

```bash
python scripts/evaluate_generation.py --prompt-version partner-copilot-v2 --parser-version parser-v1 --output /caminho/generation-p2-s1.jsonl
```

Para apenas mudar o parser use `--prompt-version partner-copilot-v1 --parser-version
parser-v2`. A CLI `partner-copilot ask` aceita as mesmas duas flags. Tambem e possivel
usar as variaveis de ambiente PROMPT_VERSION e PARSER_VERSION.
Versoes e hashes entram na identidade do experimento (schema 2), impedindo retomada
com outra combinacao. Checkpoints v1 existentes permanecem intactos; para novas
execucoes use outro arquivo. Metricas estrita/tolerante e o experimento corretivo D estao descritos em
[geracao corretiva](docs/generation-correction.md); a tolerante nao altera o parser. Detalhes: [versionamento da geracao](docs/generation-versioning.md).


### Saida estruturada e verificacao nova

O experimento corretivo D nao trouxe ganho: 25 chamadas extras, aceitacao mantida
em 2/27. Retry descartado da pipeline; artefatos historicos preservados.
q23 passou no parser e respondeu sobre embalagem, embora a pergunta fosse sobre
mensagens sem retorno. Aceitacao e sustentacao factual sao medidas separadas.

A estrategia nova e partner-copilot-json-v1 + parser-json-v1: Pydantic valida o
JSON, IDs sao conferidos diretamente no contexto e citacoes sao renderizadas por
codigo. Sem retry. A execucao dedicada usa apenas dez perguntas novas, tres negativas;
nao usa as 30 antigas para medir esse prompt. A primeira checagem JSON teve 7/10 saidas validas no esquema, IDs no contexto em
7/7 respostas estruturadas e abstencao correta em 0/3 negativas. n09 passou no
parser, mas afirmou uma analise laboratorial sem evidencia. Resultados e leitura
qualitativa estao em [verificacao JSON](reports/generation-json-v1/README.md). Defaults legados continuam disponiveis para reproducao, e o novo runner
seleciona explicitamente o par JSON.

[Analise de falhas e citacoes](docs/generation-output-analysis.md) e
[como executar a checagem JSON](docs/structured-verification.md).


### Rodada final V3

O modelo corrompeu o ID em alguns casos e ignorou o formato na maioria das 14
rejeicoes de citacao de D; nao foi encontrada review existente citada fora do
contexto nesses casos. Resultado negativo preservado, retry descartado.

partner-copilot-v3 e parser-v3 usam o primeiro objeto JSON completo, consistencia
estrutural de abstencao e fonte com trecho literal conferido por codigo. O sufixo
ignorado fica registrado; nao ha reparo de introducao ou nova tentativa. Trecho
literal nao comprova que a afirmacao decorre dele ou responda a pergunta.

A rodada congelada usa n11-n20 (3 negativas) primeiro e registra separadamente as
30 antigas com contaminated=true. Contexto de ate oito reviews. Nenhum resultado
real V3 foi obtido durante a preparacao local. [Protocolo e limites](docs/final-v3.md).
