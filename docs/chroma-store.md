# Store Chroma persistente

A implementação canônica é `partner_copilot.ingestion.chroma_store.ChromaStore`.
O import anterior em `partner_copilot.retrieval.store` é um alias para a mesma classe;
não há duas implementações. A busca semântica de baixo nível permanece no store;
limiares e decisões de retrieval pertencem ao `Retriever`.

## Construção e nome da collection

`ChromaStore()` usa `Settings.chroma_path`, `embedding_model` e o prefixo
`chroma_collection`. Caminho, modelo e collection podem ser informados explicitamente.
`PersistentClient` mantém os documentos no disco, inclusive entre processos.

Sem nome explícito, a collection é `<prefixo>-<modelo>-<hash de 8 caracteres>`.
O modelo fica legível no nome; o hash usa sua identidade completa e o contrato dos
embeddings, incluindo prefixos de documento/consulta e normalização. Nomes gerados
usam somente ASCII e até 63 caracteres. Modelos de namespaces diferentes ou modos de
prefixo diferentes não compartilham a collection automática.

`CHROMA_COLLECTION=reviews` configura o **prefixo**, não o nome final. A propriedade
`store.collection_name` e o log da ingestão mostram o nome efetivo. Batch size e dispositivo
não alteram o contrato nem o nome. O contrato completo nos metadados ainda é validado,
mesmo que nomes ou hashes coincidam. Em modo de embedding_function injetada, o nome
identifica o modelo declarado; não se deve reutilizar esse nome para outro encoder.

Para abrir um índice existente com nome literal, use
`ChromaStore(path=..., model=..., collection="nome_existente")`.
Esse modo não acrescenta sufixo, mas mantém as verificações de modelo, cosseno e
pré-processamento. A mudança do padrão de nomes não migra nem apaga collections antigas.

## API

- `upsert(reviews: list[Review]) -> None`: insere ou atualiza pelas IDs; lista vazia é no-op.
- `count() -> int`: quantidade de documentos da collection.
- `query(text, k, where=None) -> list[RetrievedDoc]`: busca básica por cosseno, com filtros.
- `reset() -> int`: remove os documentos somente desta collection e retorna a quantidade
  removida. Preserva seu ID, nome, metadados e contrato de embeddings; re-ingestão é possível.

`reset()` não usa `client.reset()` nem apaga o diretório persistente. Outras collections
permanecem intactas. IDs são lidas e removidas em lotes de até 1.000, sem carregar o modelo.
Execute durante manutenção, sem escritores concorrentes; não há transação global de reset.
A operação é destrutiva para os documentos da collection alvo, portanto precisa ser chamada
explicitamente. Não foi executada sobre índices de produção durante esta implementação.

```python
from pathlib import Path
from partner_copilot.config import Settings
from partner_copilot.ingestion.chroma_store import ChromaStore
from partner_copilot.schemas import Review

settings = Settings(chroma_path=Path("work/chroma-example"))
store = ChromaStore(settings=settings)
store.upsert(
    [
        Review(
            id="demo_001",
            restaurant_id="rest_001",
            text="A entrega atrasou.",
            rating=2,
            created_at="2026-11-01",
            category="pizza",
            bairro="Centro",
            city="São José dos Campos",
        )
    ]
)
print(store.collection_name, store.count())
docs = store.query("Atrasos", k=3, where={"city": "São José dos Campos"})
# store.reset()  # Removeria somente os documentos da collection deste exemplo.
```

## Metadados e cidade desconhecida

Os metadados persistidos por documento são escalares:

| Chave | Tipo | Finalidade |
|---|---|---|
| `restaurant_id` | str | Restaurante |
| `city` | str, quando conhecida | Cidade |
| `bairro` | str | Bairro, independente de cidade |
| `category` | str | Categoria |
| `rating` | int | Nota entre 1 e 5 |
| `created_at_int` | int YYYYMMDD | Intervalos `$gte`/`$lte` |
| `created_at` | str ISO | Data legível e reconstrução do schema |
| `item` | str | Item, ou string vazia quando não informado |
| `aspect_<nome>` | str pos/neg, quando mencionado | Filtro por aspecto |
| `aspects_json` | str JSON | Reconstrução do mapa completo |

`Review.city` é opcional, rejeita texto vazio e remove espaços externos. Os dados atuais
não informam cidade; não há inferência por bairro nem valor fictício para preencher esse campo.
A chave é omitida quando desconhecida e removida se uma atualização deixar de informá-la.
O mesmo vale para aspectos que deixam de ser mencionados. `None` é enviado apenas como
instrução transitória de exclusão, suportada pelo Chroma configurado; não é valor persistido.
Mapas/listas de aspectos não são gravados como metadados aninhados: o mapa é serializado.

## Testes

```powershell
python -m pytest tests/test_chroma_store.py -v
```

Os testes usam vetores fixos, sem download: persistência entre processos, idempotência,
reset vazio e com múltiplos lotes, isolamento entre collections/modelos, re-ingestão,
tipos dos metadados, filtros combinados, cidade opcional e compatibilidade dos imports.

## Documentos divididos e contagem de gravações

A pipeline usa `upsert_documents` com conjuntos completos de chunks por review.
Esse método retorna inseridos, atualizados e removidos obsoletos; aceita batches menores
na gravação, mas só remove os chunks antigos após gravar todos os novos.
Metadados adicionais `review_id`, `chunk_index` e `chunk_count` preservam a fonte e a ordem.
`review_ids()` retorna as IDs de origem para validar os splits, enquanto `count()` conta
documentos físicos. A query retorna ID original na review e ID física em `document_id`.
Mais detalhes em [ingestion.md](ingestion.md).
