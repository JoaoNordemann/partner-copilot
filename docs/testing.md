# Testes de ingestão e retrieval

A suíte padrão usa bancos Chroma em `tmp_path` e embeddings fake, sem baixar modelos.
Cobre reingestão idempotente, rejeição e logging de registros inválidos, preservação
após reabrir o banco, metadados escalares e filtros. O teste da pipeline persistente
confere que registros válidos antes e depois de um inválido chegam ao Chroma.

Execute na raiz do projeto:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

A sanidade semântica usa embeddings multilíngues reais na CPU, com cinco reviews
independentes dos dados de treino e gold. Para “entrega demorou muito”, as duas
reviews sobre atraso precisam superar os distratores sobre sabor, embalagem e preço.
Esse teste é opcional porque carrega o modelo; um fake não comprova semântica.

O modelo configurado por padrão deve estar baixado previamente no cache do Hugging Face.
O teste usa `local_files_only=True`: se você o habilitar sem o modelo, ele falhará.
Para o cache local usado neste projeto:

```powershell
$env:RUN_SEMANTIC_TESTS = '1'
$env:SENTENCE_TRANSFORMERS_HOME = "$PWD\work\hf-cache\sentence-transformers"
$env:HF_HUB_OFFLINE = '1'
.\.venv\Scripts\python.exe -m pytest tests/test_semantic_retrieval.py -v
Remove-Item Env:RUN_SEMANTIC_TESTS
Remove-Item Env:SENTENCE_TRANSFORMERS_HOME
Remove-Item Env:HF_HUB_OFFLINE
```

Se usar o cache padrão do Hugging Face, omita `SENTENCE_TRANSFORMERS_HOME`.
O banco criado pelo teste é temporário; o índice persistente do projeto permanece intacto.
A sanidade verifica um exemplo controlado e não substitui uma avaliação de retrieval.
