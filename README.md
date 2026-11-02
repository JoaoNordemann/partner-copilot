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
