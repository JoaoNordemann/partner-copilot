# API HTTP do PartnerCopilot

## Iniciar

```powershell
python -m pip install -e ".[dev]"
$env:LLM_BACKEND = "real"
python -m uvicorn partner_copilot.api:app --host 127.0.0.1 --port 8000 --workers 1
```

Configurar CHROMA_PATH para um índice persistido do split RAG e o mesmo modelo de
embedding. A API não cria/reingere índices vazios ao errar um caminho. Para preparar
a base operacional num clone novo, usar scripts/ingest.py com as configurações
do guia. Neste ambiente foi preparado também um índice RAG em work/api-cpu-benchmark/chroma
para a medição CPU; essa pasta é local/ignorada e não acompanha um clone.

O embedder usa CPU e cache em API_EMBEDDING_CACHE, sem download por padrão. Se
precisar baixar explicitamente, configurar API_ALLOW_MODEL_DOWNLOAD=true antes
de iniciar. Índice, modelo de embedding e backend são tentados uma vez no lifespan;
requisições reutilizam os recursos. Falhas não disparam carga/retry por pergunta.
Reiniciar o processo para trocar backend/configuração ou recuperar um componente.

Usar um único worker por GPU: o semáforo é do processo, não uma fila distribuída.
Modelo real indisponível não derruba a aplicação: /health retorna 503 e identifica
llm como unavailable; menus/recusa sem LLM podem continuar funcionando se o índice
estiver disponível. Configuração de backend ausente/inválida falha antes de iniciar.

## Endpoints

- GET /health: 200 quando os componentes necessários estão prontos, 503 em degradação;
  estado de index, embedder, llm e replay sem mensagens internas/segredos.
- POST /ask: DTO estrito, resposta api-v1 com objeto v3, texto renderizado, fontes,
  abstenção, modo e tempos. /v1/ask é alias do mesmo contrato.
- GET /restaurants: nomes/IDs e itens presentes no índice, carregados em memória.
- GET /restaurants/{restaurant_id}/items: itens do restaurante selecionado.
- Os endpoints de saúde e menus também possuem aliases /v1. /docs expõe OpenAPI.

```json
{
  "restaurant_id": "rest_001",
  "question": "Quais avaliações mencionam atraso?",
  "filters": {"aspect": "tempo_entrega"},
  "k": 8
}
```

Pergunta até 2.000 caracteres, não vazia; k inteiro 1..12; restaurant_id obrigatório.
Período opcional usa start_date/end_date ISO, inclusive, com início <= fim. Item é
igualdade exata. Aspecto seleciona rótulo negativo (reclamações). Campos extras são
rejeitados. Consulta que excede a janela de tokens do embedder é rejeitada com 422,
mesmo que caiba no limite de caracteres, sem truncamento silencioso.

API_PROMPT_VERSION/API_PARSER_VERSION pertencem ao perfil v3 da API; as configurações
PROMPT_VERSION/PARSER_VERSION legadas da CLI permanecem inalteradas. Sem contexto,
retorna abstenção 200 sem chamar backend, mesmo se o modelo real estiver indisponível.

## Modos honestos

- real: Mistral NF4 em GPU, carregado no startup; nenhuma substituição silenciosa.
- fake: resposta JSON fixa; a padrão é abstenção. API_FAKE_RESPONSE_PATH permite
  fixture explícita. Sempre is_simulation=true e rótulo SIMULAÇÃO. Não mede qualidade
  ou latência de um LLM. Com índice real, embedding e busca continuam reais em CPU.
- replay: nenhuma busca/embedding/LLM ao vivo; resposta/contexto de arquivo aprovado,
  chave exata da requisição, hashes e validação v3. is_replay=true; rótulo REPLAY e
  origem/hardware/histórico em source_run. Tempos atuais de geração/busca são null.

O exemplo de catálogo tem entries vazio de propósito: não existe ainda aprovação
humana de uma saída v3 aceita na seleção revisada. Isso deixa replay indisponível
(503), sem respostas fabricadas. Para curadoria, aprovar explicitamente uma gravação
v3 já existente e criar um catálogo fora dos dados reservados; não fazer inferência
nova apenas para preencher a demo. Não transformar C/q05 legado em gravação v3.

Cada entrada de catálogo precisa de source_file/source_sha256, question_id,
approval_file/approval_sha256 e corpus_file/corpus_sha256. Paths relativos ao catálogo.
A aprovação referencia o mesmo caso/coorte num JSONL de revisões humanas completed,
sustentada e answers_question=sim. Snapshots/versões, texto de fonte e filtros são
conferidos na carga. Dados ficam em memória; alterar arquivos em disco não altera
o snapshot servido sem reiniciar o serviço. Configuração divergente é 409;
pergunta/filtros/k sem chave exata é 404. Nenhuma similaridade escolhe gravações.

## Concorrência e timeout

API_MAX_PENDING=8 limita trabalhos aceitos (incluindo os que expiraram e ainda
estão encerrando); fila cheia retorna 429 resource_busy. O semáforo serializa a
etapa de geração. API_REQUEST_TIMEOUT_S=60 limita a espera HTTP inteira. Ao expirar,
504 é devolvido; CUDA/thread não são cancelados de forma insegura. O trabalho
mantém o semáforo até terminar e sua saída atrasada é descartada. Um request que
expirou na fila não inicia inferência. No shutdown, aguardar tarefas já iniciadas.
Não existe retry automático nem fallback para outro backend.

## Tempos e erros

metadata.timings_ms inclui embedding_ms e search_ms medidos diretamente, além do
intervalo embedding_search_ms, generation_ms, queue_ms, validation_ms e total_ms.
Busca inclui count/query, filtros/corte e conversão dos documentos; embedding inclui
tokenização/checagem de limite. Queue é subconjunto da etapa generation, não somar
novamente. Nenhum tempo de CPU é inferido por subtração. Validação cobre schema,
IDs, trechos e DTO, não sustentação semântica. Histórico da T4 fica em source_run,
separado do hardware e dos tempos atuais.

Erros: 422 invalid_request; 502 generation_contract_failed; 503 model_unavailable,
retrieval_unavailable ou replay_unavailable; 404 replay_not_found; 409
replay_snapshot_mismatch; 504 backend_timeout; 429 resource_busy. Exceção inesperada
é 500 internal_error em envelope próprio. Erros não retornam texto bruto, resposta
parcial, prompts, tokens ou stack trace. X-Request-ID também vem no corpo/metadados.

Logs JSON registram ID gerado pelo serviço, restaurante, backend, versão do prompt,
latências, status e tipo/código de erro. Não registram pergunta, reviews, resposta
ou prompts. Isso reduz exposição, mas não certifica conformidade LGPD; uso com dados
reais requer política própria de anonimização, acesso e retenção.

## Medição única de CPU

[Resultado e ambiente reais](../reports/api-cpu-latency-v1/README.md). Foram usadas
40 amostras do componente de retrieval da API, sem HTTP/GPU/LLM, após warm-up,
com 862 reviews do RAG e hardware/threads explícitos. Não são tempos de Mistral,
nem um SLA de produção. Os arquivos anteriores continuam snapshots históricos.
O script se recusa a sobrescrever resultados existentes; não repetir para selecionar
um resultado favorável. O snapshot exato do script medido está preservado no relatório;
a única diferença na versão final é quebra de linha, com AST idêntica registrada.

Testes sem GPU cobrem startup único/degradado, erros e privacidade dos logs, validação,
menus, replay exato/recusado, serialização e retenção do semáforo após timeout.

## Testes e CI sem runtime de ML

O workflow `retriever-unit.yml` verifica Python 3.12 e 3.13 no Linux. 3.13 acompanha
o ambiente Kaggle registrado; 3.12 cobre uma versão amplamente usada em servidores.
O mínimo 3.10 do pyproject é uma faixa de instalação, não uma promessa de teste
em todas as versões. O ambiente local Windows usa 3.14 e é verificado separadamente.
A matriz CPU não certifica compatibilidade CUDA/quantização nessas versões.

O CI instala somente `requirements-ci.txt`, sem `pip install -e .`, torch, Chroma ou
pesos. O setup-python mantém cache pip identificado por esse arquivo. Ruff fica na
versão 0.17.3 para que formatação não mude silenciosamente. Pytest usa uma lista
explícita de testes sem dependências de ML, com `-m "not gpu"`; testes que precisam
de Chroma ou embeddings reais continuam fora dessa instalação mínima.

`tests/test_api_dependencies.py` inicia outro processo com imports de torch,
transformers, sentence-transformers, Chroma, bitsandbytes, accelerate e HF Hub
bloqueados. Ele importa a API e executa os testes fake/replay, em modo offline.
Isso detecta imports pesados mesmo quando os pacotes existem na máquina local.

Para repetir o contrato da API localmente:

```powershell
python -m pytest tests/test_api.py tests/test_api_replay.py tests/test_api_dependencies.py -m "not gpu" -v
python -m ruff check .
python -m ruff format --check .
```
