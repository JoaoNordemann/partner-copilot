# Configuração

`Settings`, em `src/partner_copilot/config.py`, centraliza paths, modelos e parâmetros.
Copie `.env.example` para `.env` e ajuste os valores locais. Nunca versione tokens.
O token do Hugging Face é opcional para modelos públicos; modelos restritos exigem acesso.

Precedência: argumentos explícitos da CLI/construtor > ambiente > `.env` > defaults.
Paths relativos são resolvidos a partir do diretório de execução. Execute os comandos
na raiz do repositório, ou configure paths absolutos.

`DATA_RAW_DIR` define `reviews.jsonl`; `DATA_GOLD_DIR` define `prior_exposure.json`;
`DATA_EXTERNAL_DIR` define a pasta `b2w_reviews01`. `DATA_SPLITS_DIR` mantém as partições
registradas, e a ingestão continua aceitando apenas o split RAG validado.
Alterar paths não regenera nem move os snapshots. Dados externos continuam separados do índice.
Seeds, revisões e hashes dos datasets fazem parte do protocolo reprodutível e permanecem fixos.

`EMBEDDING_MODEL` controla os embeddings; `LLM_MODEL_ID`, `MAX_NEW_TOKENS`,
`TEMPERATURE` e `TOP_P` controlam o Mistral. Temperatura zero desativa amostragem.
O nome automático da collection inclui a identidade do contrato de embeddings.
Trocar o modelo requer uma collection compatível ou nova ingestão.

`get_settings()` mantém cache por processo. Após mudar o ambiente em um processo
Python já aberto, use `get_settings.cache_clear()` ou reinicie o processo.
O `.env.example` documenta também limites de ingestão, retrieval e dispositivos.

```powershell
Copy-Item .env.example .env
# Edite .env antes de executar a ingestão.
.\.venv\Scripts\python.exe scripts/ingest.py --help
.\.venv\Scripts\python.exe -m pytest -v
```
