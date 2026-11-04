# Consulta pela CLI ask

A entrada liga a collection persistente, o Retriever e a RAGPipeline ao provider de
geração. A instalação editável local foi atualizada sem baixar dependências para
registrar `partner-copilot ask`. Também há o atalho `scripts/ask.py`.

## Uso

Execute na raiz do repositório, depois de ingerir o split RAG registrado:

```powershell
.\.venv\Scripts\python.exe scripts/ingest.py
.\.venv\Scripts\partner-copilot.exe ask "Quais reclamações de entrega aparecem nas avaliações?" --restaurant-id rest_002
```

Versão com filtros e saída de máquina:

```powershell
.\.venv\Scripts\python.exe scripts/ask.py "O que foi relatado sobre a entrega nesse período?" --restaurant-id rest_002 --start-date 2026-10-19 --end-date 2026-11-01 --json
```

Também pode usar `python -m partner_copilot.cli ask ...`. O modo texto mostra resposta,
fontes, abstenção/motivo e metadados. `--json` devolve o Answer serializado em stdout,
incluindo métricas de geração quando disponíveis. Logs usam stderr.

Flags: --db-path, --collection (nome literal existente), --embedding-model,
--llm-model, --retrieval-k, --context-k, --min-score, --temperature, --seed,
--max-new-tokens e --prompt-version. Filtros: --aspect (polaridade negativa), --item,
--category, --city, --bairro, --start-date e --end-date. Datas são inclusivas.
Argumentos explícitos prevalecem sobre ambiente, .env e defaults.

O nome automático da collection é o mesmo da ingestão, baseado no modelo e no contrato
dos embeddings. Não mude o embedding para consultar vetores de outro modelo. Se usar
uma collection antiga com nome literal, informe --collection; sua identidade/métrica
continuam validadas. Sem índice, collection ou split RAG válido, a entrada falha antes
de chamar o LLM. Não cria/reset/ingere um índice durante ask. O cliente Chroma não é
uma conexão SQLite somente leitura; a aplicação de consulta não executa upsert/reset.

A aplicação verifica IDs contra o RAG registrado, inclusive resolvendo chunks para
suas reviews. Uma collection gold/train_pool é rejeitada. A CLI de produção não é o
runner de avaliação isolada; esse isolamento é intencional.

## Abstenção e citação inválida

Sem resultados após os filtros e limiar, a pipeline devolve a frase fixa de abstenção
com retriever_empty, llm_called=false e generation=null, sem carregar pesos do Mistral.
O embedding ainda pode ser necessário para uma busca em collection não vazia.
Se houver documentos, o provider chama o LLM e o marcador exato pode produzir
llm_insufficient_evidence, mantendo contagens e métricas reais da chamada.

Cada citação deve ser ID de review presente no contexto realmente enviado ao LLM.
É uma condição mais estrita que estar entre todos os documentos recuperados: uma
review excluída pelo limite de contexto também não pode ser citada. IDs de chunks
não substituem os review_id usados no prompt. Repetições válidas são deduplicadas
em sources na ordem da primeira citação.

**Política: falhar a resposta inteira.** Não removemos uma fonte inventada e publicamos
a afirmação restante, nem convertemos esse erro em abstenção bem-sucedida. O parser
lança InvalidCitationError, subtipo de GenerationContractError, com diagnóstico
contável; a pipeline registra generation_rejected com código e contagem, sem publicar
a resposta do modelo. A classe de erro mantém compatibilidade com quem já captura
a violação geral de contrato.

No modo --json, uma falha de citação produz em stdout uma estrutura como esta
(exemplo de protocolo, não saída real do Mistral):

```json
{
  "error": {
    "code": "invalid_citation",
    "message": "Citation references a review outside the context",
    "invalid_ids": ["fonte_inventada"],
    "invalid_citation_count": 2,
    "allowed_context_ids": ["fonte_a"]
  }
}
```

Duas referências ao mesmo ID inválido contam como duas ocorrências e um ID único.
Conte registros error.code=invalid_citation para respostas rejeitadas, e some
invalid_citation_count para referências inválidas. Use o total de tentativas como
denominador e reporte as unidades; não esconda falhas retirando-as da avaliação.
Um ID válido não garante suporte semântico: detectar afirmações sem evidência ainda
exige avaliação de geração. Citação inventada é um sinal direto de falha de fonte,
não uma medição completa de todas as formas de alucinação.

## Códigos de saída

| Código | Significado |
| ---: | --- |
| 0 | Resposta ou abstenção válida. |
| 1 | Falha de execução, por exemplo indisponibilidade da GPU; ver logs. |
| 2 | Configuração, filtros ou preflight inválidos. |
| 3 | Citação fora do contexto: resposta rejeitada. |
| 4 | Outra violação de formato/contrato de geração. |

Em --json, erros de aplicação usam stdout com chave error e código de saída não zero.
Erros de sintaxe de argumentos seguem argparse no stderr. No modo texto, erros vão
para stderr. Não misture stderr com stdout se for interpretar a saída JSON.

A implementação continua exigindo CUDA para Mistral4bit. Ajuda, validação de argumentos
e abstenção antes de inferência podem ser usadas sem carregar esse modelo. Não foi
realizada avaliação de qualidade com Mistral real neste ambiente CPU.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_ask_cli.py tests/test_ask_integration.py tests/test_generation_prompt.py -v
```

Unitários cobrem precedência de configuração, filtros, modos texto/JSON, erros contáveis
e ajuda/preflight com Chroma e frameworks de modelo explicitamente bloqueados. Integração
usa Chroma persistente em tmp_path, embedder fake e LLM fake: pergunta sem resultados,
resposta com fonte válida, citação repetida inventada, preservação da base e rejeição de
IDs fora do RAG. O grupo unitário foi adicionado ao workflow leve de CI.
