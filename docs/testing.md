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

## Testes de geração sem GPU e execução real opt-in

O grupo leve usa retriever e LLM falsos e não carrega pesos. Verifica explicitamente:

- Retrieval vazio: abstained=true, retriever_empty e llm.generate.assert_not_called().
- Prompt efetivamente recebido pelo LLM falso: IDs das fontes, exigência de evidência
  explícita, citações, marcador de abstenção e instruções de dados não confiáveis.
- Citação inexistente em qualquer documento recuperado: InvalidCitationError com
  contagem de ocorrências. Também verifica citação de review recuperada mas não enviada.
- Marcador [[SEM_EVIDENCIA]] emitido pelo LLM: llm_insufficient_evidence, frase pública
  fixa, fontes vazias e chamada ao LLM confirmada. Uma recusa livre ou a frase pública
  emitida diretamente sem o marcador não substitui o protocolo interno.

Comando equivalente ao grupo leve de CI:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_retriever.py tests/test_retriever_dependencies.py tests/test_generation_prompt.py tests/test_generation_provider.py tests/test_ask_cli.py -m "not gpu" -v
```

O teste real está em tests/test_generation_gpu.py, marcado gpu. Por padrão o conftest
aplica skip antes de executar fixtures de GPU; o CI também usa seleção explícita de
arquivos leves e -m "not gpu". Para habilitar deliberadamente em uma máquina com CUDA,
bitsandbytes compatível e pesos/tokenizer Mistral v0.2 já disponíveis em cache:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_generation_gpu.py --run-gpu -m gpu -v -s
```

O fixture carrega uma instância real para os dois casos sintéticos (resposta com
citação e abstenção por informação ausente), usando seed 42 e temperatura 0. Os loaders
reais recebem local_files_only=True: não há download automático. Sem CUDA o teste é
ignorado com motivo explícito; com CUDA e cache incompleto, falha sem baixar pesos.
O retriever continua falso para isolar a geração; tokenizer, pesos NF4 e inferência
são reais. A saída inclui os metadados medidos quando a execução acontece.

As perguntas desse teste não vêm do eval set. Um caso real de abstenção não substitui
uma avaliação da taxa de abstenção; se a versão v1 falhar, registrar o erro e preservar
o template antes de criar v2. Neste ambiente CPU, o teste real não foi executado.
