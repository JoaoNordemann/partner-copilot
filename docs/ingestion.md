# Pipeline de ingestão

A API canônica é `partner_copilot.ingestion.pipeline.IngestionPipeline`.
Ela lê JSONL em streaming, valida registros com Pydantic, cria documentos por review/chunk,
gera embeddings em lotes pelo store e faz upsert. `scripts/ingest.py` usa essa API.
O helper anterior em `ingestion/indexer.py` e o loader de validação estrita continuam
fail-fast por compatibilidade; eles não são a pipeline tolerante usada pela CLI.

## IDs e idempotência

- `id` existente é preservada; `review_id` é aceito como alias de entrada quando não há `id`.
- Se ambos estiverem ausentes, a ID é `review_` + SHA-256 de restaurante, data ISO e texto
  exato. Nota e aspectos não participam desse hash, permitindo atualizar essas informações.
- Sem ID autoritativa, duas reviews do mesmo restaurante/data/texto são consideradas a mesma
  entrada; mudar texto ou data gera outra identidade. Prefira IDs de origem quando existirem.
- Reviews curtas mantêm sua ID como ID do documento.
- Reviews divididas recebem IDs `chunk_` + SHA-256 de ID original e índice do chunk.
- Duplicatas dentro do arquivo são ignoradas: a primeira linha válida vence, inclusive em
  conflito. O log informa linha e existência de conflito, sem imprimir o texto.
- Repetir a execução atualiza os mesmos documentos. Não há remoção de reviews ausentes do arquivo.

O store verifica propriedade da ID para evitar sobrescrever documento de outra review.
Quando o número de chunks muda, documentos obsoletos da mesma review são removidos somente
após todos os novos chunks terem sido gravados. Falhas podem deixar gravações parciais;
a próxima execução com a mesma fonte corrige o estado sem duplicar. Não há transação global.
Execute uma ingestão por collection, sem escritores concorrentes para a mesma review.

## Chunking por tokens

A estratégia é **uma review = um documento quando cabe no modelo**. Textos maiores são
janelas de tokens, por offsets de caracteres do tokenizador real, com 16 tokens de overlap.
Não cortamos por quantidade arbitrária de caracteres nem descartamos o final silenciosamente.

O limite efetivo considera `max_seq_length` do modelo, tokens especiais e prefixo de documento
(`passage: ` para E5). Cada trecho é retokenizado com prefixo e tokens especiais para confirmar
que cabe. Um limite configurado menor que o do modelo pode ser usado; nunca o aumenta.
O splitter exige tokenizador rápido com offsets. O modelo/tokenizador só carregam no primeiro
registro válido que precisa de processamento. Uma entrada composta apenas por linhas inválidas
não carrega pesos. Um token isolado que não caiba é registrado como entrada inválida.

Configurações:

- `INGESTION_CHUNK_OVERLAP_TOKENS=16`.
- `INGESTION_CHUNK_MAX_TOKENS` opcional: quando omitido, usa o limite real do modelo.
- `INGESTION_MAX_REVIEW_CHARS=50000`: limite operacional de segurança; maiores são ignoradas.
- `EMBEDDING_BATCH_SIZE=32`: lote de inferência.
- `scripts/ingest.py --batch-size 128`: lote de documentos para gravação.

O limite precisa comportar overlap, prefixo e tokens especiais. Configuração impossível é
fatal, não um motivo para descartar silenciosamente todas as reviews.
Os trechos podem terminar dentro de uma frase; a sobreposição reduz perda de contexto,
mas não constitui um splitter semântico de sentenças. Todos os trechos são substrings da fonte.

## Fontes e metadados

Cada documento persiste `review_id` original, `chunk_index` e `chunk_count`, além dos campos
filtráveis existentes. A consulta retorna `RetrievedDoc.review.id` como ID original,
`document_id` como ID física do chunk e os índices de chunk, preservando citações da fonte.
O texto retornado é o trecho encontrado. Agrupamento e deduplicação de resultados por review
ficam para a camada de retrieval, não são implementados nesta mudança.

Nota e aspectos continuam sendo metadados da review inteira; não são anotações independentes
de cada trecho. Não use essa propagação como gold ou como anotação de spans para ABSA.

`store.review_ids()` resolve IDs de chunks para IDs de origem na proteção dos splits.
Gold e train_pool continuam fora do RAG. A CLI confere o manifesto antes de carregar modelos:
fonte divergente, split adulterado ou coleção contendo reviews fora do RAG são erros fatais.
Isso é diferente de registros inválidos em um arquivo passado à API genérica da pipeline.
Não afrouxamos a proteção do snapshot só para aceitar um arquivo modificado.

## Contadores e erros

Os eventos `ingestion_started`, `ingestion_progress` e `ingestion_completed` registram:

| Campo | Significado |
|---|---|
| `lines_read` | Linhas físicas, incluindo vazias |
| `read` | Registros não vazios lidos |
| `valid` | Registros válidos, incluindo duplicatas válidas ignoradas |
| `invalid` | JSON, schema, tamanho ou conteúdo de chunk inválido |
| `duplicates`, `blank` | Duplicatas e linhas vazias ignoradas |
| `ignored` | invalid + duplicates + blank |
| `reviews_upserted` | Reviews únicas gravadas com sucesso |
| `documents_upserted` | Documentos/chunks gravados |
| `inserted`, `updated` | Documentos novos/existentes, conferidos antes do upsert |
| `stale_deleted` | Documentos antigos da mesma review removidos após nova gravação |
| `batches` | Lotes completos da pipeline; inferência pode usar lotes internos menores |

Ao terminar com sucesso: `read = valid + invalid`, `lines_read = read + blank` e
`reviews_upserted = valid - duplicates`. Os contadores são de documentos quando indicado;
uma review dividida pode gerar mais de um documento. Leituras prévias para contagem não
são transações de isolamento contra escritores externos concorrentes.

JSON inválido, campos inválidos, texto vazio e limite de caracteres excedido não derrubam
as linhas seguintes. Logs incluem número da linha e motivo/campo, sem conteúdo dos registros.
Falhas de disco, Chroma, modelo, tokenizador ou integridade interrompem o processo e nunca
são reportadas como execução completa bem-sucedida. Lotes anteriores podem permanecer gravados;
reexecutar é seguro. Problemas de arquivo/encoding também são fatais.

## Uso

```powershell
python scripts/ingest.py --batch-size 128
python -m pytest tests/test_ingestion_pipeline.py -v
```

API genérica para uma fonte própria já autorizada:

```python
from pathlib import Path
from partner_copilot.ingestion.chroma_store import ChromaStore
from partner_copilot.ingestion.chunking import TokenTextSplitter
from partner_copilot.ingestion.pipeline import IngestionPipeline

store = ChromaStore(path="work/ingestion-example")
splitter = TokenTextSplitter(store.embedder, overlap_tokens=16)
report = IngestionPipeline(store, splitter, batch_size=128).run(Path("minhas_reviews.jsonl"))
print(report.to_dict())
```

A API genérica não seleciona dados nem garante autorização de uma fonte por si só.
Para o índice RAG do projeto, use a CLI, que mantém as verificações de splits.
## Validação executada

A suíte completa passou com 114 testes. Lint, formatação e integridade do diff passaram.
Os testes misturam JSON inválido, schema inválido, duplicatas, linhas vazias e linhas válidas,
confirmando que registros posteriores continuam sendo gravados e que falhas do modelo/store
não são confundidas com entradas inválidas.

Com o MiniLM real em cache e collections temporárias em `work/`:

- O split RAG de 862 reviews gerou 862 documentos, sem inválidos ou duplicatas no arquivo.
- Primeira execução: 862 inseridos; segunda: zero inseridos e 862 atualizados.
- O maior texto desse split usou 87 tokens, abaixo do limite observado de 128.
- Uma review artificialmente alongada foi dividida em quatro chunks; repetir a execução
  atualizou os quatro sem inserir novos. Ao encurtar a mesma review, os quatro chunks antigos
  foram removidos e restou um documento. Todos os chunks respeitaram o limite real do modelo.
- As citações mantiveram a ID original, e os IDs de origem no índice RAG corresponderam
  exatamente ao manifesto, sem gold ou train_pool.

Dados brutos, snapshots de anotação e splits não foram modificados pela validação.

## Entrada por CLI

A entrada aceita `--input`, `--db-path`, `--model` (alias `--embedding-model`),
`--batch-size` e `--reset`. Argumentos explícitos prevalecem sobre `.env` e ambiente.
A orquestração fica em `ingestion/service.py`, não no script de argumentos.
O reset explícito é limitado à collection selecionada e só acontece após validar a fonte
e preparar o modelo/tokenizador. Consulte [ingestion-cli.md](ingestion-cli.md).
