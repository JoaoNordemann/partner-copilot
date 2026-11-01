# PartnerCopilot

RAG modular para análise de avaliações de restaurantes. Os dados gerados são
sintéticos e não representam dados reais do iFood.

## Ingestão

Execute a partir da raiz do projeto, em um ambiente Python compatível:

```powershell
python -m pip install -e ".[dev]"
python scripts/generate_synthetic_data.py --n 3000 --seed 42 --end-date 2026-11-01 --validate
python scripts/ingest.py --batch-size 128
python -m pytest
python -m ruff check .
```

Configure `.env` a partir de `.env.example`. A ingestão usa `DATA_RAW_DIR`,
`CHROMA_PATH`, `CHROMA_COLLECTION` e `EMBEDDING_MODEL`. O primeiro uso do embedding
precisa baixar o modelo multilingual; a ingestão não carrega o Mistral e não exige GPU.
`--input caminho/reviews.jsonl` permite escolher outro arquivo.

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
