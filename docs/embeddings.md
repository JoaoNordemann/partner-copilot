# Embeddings multilíngues

## Interface e configuração

`src/partner_copilot/ingestion/embedder.py` define `SentenceTransformerEmbedder` e o protocolo
`Embedder`. O módulo não carrega nem importa Sentence Transformers na inicialização.
O primeiro pedido não vazio instancia o modelo; chamadas seguintes reutilizam a instância.
Uma lista vazia retorna `[]` sem carregar pesos. Cada processo/worker mantém sua instância.

```python
from partner_copilot.ingestion.embedder import SentenceTransformerEmbedder

embedder = SentenceTransformerEmbedder()  # Somente configuração; ainda não carrega o modelo.
documents = embedder.embed_documents(["A entrega atrasou.", "A embalagem estava aberta."])
query = embedder.embed_query("Por que os clientes estão reclamando?")
```

| Variável | Padrão | Função |
|---|---|---|
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Modelo carregado |
| `EMBEDDING_BATCH_SIZE` | `32` | Máximo de textos por lote de encode |
| `EMBEDDING_DEVICE` | `cpu` | Dispositivo explícito; pode usar `cuda` quando disponível |
| `EMBEDDING_PREFIX_MODE` | `auto` | `auto`, `none` ou `e5` |

O lote de ingestão (`scripts/ingest.py --batch-size`) controla quantas reviews são enviadas
por upsert; o lote de embeddings controla a inferência dentro desse lote. São parâmetros
independentes. O módulo retorna listas de floats, valida formato, dimensão e valores finitos,
e normaliza os vetores em L2. Entradas vazias ou vetores degenerados causam erro explícito.

## Português, modelos e prefixos

O config já escolhia o MiniLM multilíngue antes desta alteração. Não havia troca necessária
do modelo inglês; a mudança é encapsular a inferência antes delegada ao Chroma.

Com `EMBEDDING_MODEL=intfloat/multilingual-e5-small`, o modo `auto` acrescenta `passage: `
aos documentos e `query: ` às consultas, inclusive para português, conforme o
[model card oficial](https://huggingface.co/intfloat/multilingual-e5-small#usage).
O MiniLM não recebe esses prefixos. O modo `none` os desativa; `e5` os força, permitindo
usar uma cópia local do modelo sem depender do nome do diretório.

Passe os textos brutos aos métodos, sem adicionar prefixos manualmente. A chamada `encode`
suprime prompts salvos no modelo com `prompt=""`, para que nosso prefixo não seja duplicado.
Essa configuração segue a [API do Sentence Transformers](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html).
Para modelos com protocolos diferentes, como variantes com instruções, confira o model card
antes de usar; a configuração aqui foi definida para MiniLM e E5-small.

## Integração com Chroma

`ChromaStore` instancia o embedder de forma lazy. Documentos são enviados por `embeddings=`
e consultas por `query_embeddings=`; o Chroma não seleciona outro modelo implicitamente.
`embedding_function` continua disponível como caminho explícito de compatibilidade/injeção,
mas não pode ser combinado com `embedder` na mesma instância.

A coleção registra modelo, normalização e prefixos. Troca de modelo ou de pré-processamento
incompatível exige outra coleção e novo índice, inclusive se ambos os modelos tiverem
384 dimensões. Alterar somente batch size ou dispositivo não altera esse contrato.
Coleções legadas do MiniLM multilíngue, já normalizadas e sem prefixos, são compatíveis;
um índice E5 sem registro dos prefixos é recusado. Nada é apagado automaticamente.

A interface isolada de embeddings não divide textos. A pipeline de ingestão usa
`TokenTextSplitter` com o tokenizador e o limite reais, evitando truncamento dos documentos
que processa. O uso direto de encode fora da pipeline ainda deve respeitar o contexto. Não há cache de vetores entre execuções. Trocar o modelo também exige
reavaliar o limiar de similaridade do retrieval, além de reconstruir o índice.

## Pré-requisitos conferidos

- `src/`, `tests/`, `scripts/`, `pyproject.toml`, Ruff e pytest já estão configurados.
- Os 3.000 registros sintéticos e os splits estão versionados.
- Os 200 textos públicos estão em `data/external/`, com origem/licença documentadas e fora
  do Git conforme a decisão anterior. Não são incorporados ao índice RAG.
- O schema validado usa `id` como ID da review e `created_at` como data, com
  `created_at_int` para filtros. Não renomeamos esses campos para `review_id` e `date`.
- `category` e `bairro` já existem. Não inferimos `city` a partir de bairro.
- O formato externo continua separado; não inventamos restaurante ou bairro para reviews
  de e-commerce. A ingestão padrão continua limitada ao split RAG.

## Verificação

```powershell
python -m pytest tests/test_embedder.py -v
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

Os testes automatizados não baixam pesos. Verificam lazy loading (inclusive importação),
reuso do modelo, batching, normalização, validações, prefixos E5, upsert/query com Chroma
persistente e rejeição de pré-processamento incompatível antes de carregar o modelo.
A qualidade semântica entre os modelos precisa de uma avaliação separada.

O store canônico está em `ingestion/chroma_store.py`; o import antigo é um alias.
O nome automático da collection também inclui modelo e hash do contrato de embeddings.
Consulte [chroma-store.md](chroma-store.md) para nomes explícitos, persistência e reset.
