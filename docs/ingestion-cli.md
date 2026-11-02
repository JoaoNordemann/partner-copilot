# CLI de ingestão

`scripts/ingest.py` usa argparse e se limita a argumentos, configuração, apresentação de
resultados e códigos de saída. A orquestração está em `ingestion/service.py`; validação
de splits, chunking, embeddings e gravação continuam nos respectivos módulos.

| Argumento | Padrão | Uso |
|---|---|---|
| `--input` | `DATA_SPLITS_DIR/rag.jsonl` | Caminho do arquivo de dados |
| `--db-path` | `CHROMA_PATH` | Diretório persistente do banco |
| `--model` / `--embedding-model` | `EMBEDDING_MODEL` | Modelo de embeddings |
| `--batch-size` | `128` | Lote de documentos por gravação; inteiro positivo |
| `--reset` | desativado | Limpa somente a collection selecionada antes de reingerir |

Argumentos explícitos prevalecem sobre ambiente e `.env`, seguidos dos defaults de Settings.
As configurações são validadas novamente; não se modifica a instância global em cache.
O lote de inferência é independente e continua configurado por `EMBEDDING_BATCH_SIZE`.
`--input` seleciona o caminho, mas não dispensa a proteção do split RAG registrado:
corpus bruto integral, gold e treino não se tornam entradas autorizadas por usar outro caminho.

## Executar

A partir da raiz do repositório, no PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts/ingest.py --help

.\.venv\Scripts\python.exe scripts/ingest.py `
  --input data/splits/rag.jsonl `
  --db-path data/chroma `
  --model paraphrase-multilingual-MiniLM-L12-v2 `
  --batch-size 128
```

Para reconstruir intencionalmente a collection selecionada, acrescente `--reset` ao comando.
Sem essa flag, a ingestão faz upsert e não limpa a collection antes de processar os dados.
O nome automático usa o prefixo `CHROMA_COLLECTION`, o modelo e o hash do contrato dos vetores;
`--reset` não limpa outras collections no mesmo diretório nem collections de outros modelos.

## Ordem do reset

1. Validar parâmetros, existência e integridade do arquivo contra os splits.
2. Abrir somente o store selecionado e validar seu contrato de embeddings.
3. Preparar tokenizador/modelo e conferir o orçamento efetivo de tokens.
4. Com `--reset`, remover os documentos dessa collection e registrar quantos foram removidos.
5. Executar a pipeline e apresentar relatório, nome efetivo, caminho e total de documentos.

Uma entrada inválida não abre nem limpa o banco. Falha ao preparar modelo/tokenizador
não apaga documentos. Sem reset, IDs fora do RAG continuam bloqueando uma collection antiga.
Com reset explícito, essa collection pode ser esvaziada e reconstruída a partir do RAG
validado. O reset preserva a identidade/configuração da collection.

A pré-validação não transforma reset e re-ingestão em uma transação: falhas posteriores
ao reset podem deixar uma collection vazia ou parcialmente reingerida. Reexecutar é
idempotente; execute em manutenção, sem escritores concorrentes na mesma collection.
Nenhum reset de produção foi executado durante o desenvolvimento desta CLI.

## Códigos de saída e testes

- `0`: concluído com relatório; inclui entradas inválidas ignoradas pela API da pipeline.
- `2`: argumentos/configuração ou pré-validação de entrada/collection inválidos.
- `1`: falha operacional do modelo, tokenizador, armazenamento ou execução.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_ingest_cli.py -v
```

Os testes verificam precedência das flags, ajuda sem iniciar ingestão, argumentos inválidos,
reset restrito à collection, preparação do modelo antes de exclusão, preservação dos dados
em falhas e códigos de saída. Não baixam modelos nem acessam índices de produção.
