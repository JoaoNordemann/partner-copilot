# Container CPU

A imagem CPU foi construída com o alvo `cpu` e executada com o backend
`fake` em um runner Ubuntu do GitHub Actions. O healthcheck do Docker marcou
o container como saudável. O volume inicializou o índice com 862 documentos,
e `/health` e `/ask` retornaram HTTP 200. A resposta de `/ask` indicou
simulação e abstenção conforme o contrato do backend falso.

A inspeção da imagem antes do bootstrap confirmou UID e GID 10001 e ausência
de `.env` e de arquivos de pesos em `/app`, `/state` e `/home/copilot`.
O caminho GPU fica **não testado em container**.
[Build, inspeção e respostas HTTP](https://github.com/JoaoNordemann/partner-copilot/actions/runs/43225980422/job/131209151066)

Foi verificado no Windows um bootstrap real com encoder CPU já em cache:
primeira chamada reconstruiu o RAG e segunda chamada reutilizou o índice, sem
downloads. Isso valida a lógica de ingestão local, não o sistema Linux da imagem.

## Construir e executar

Instalar Docker Desktop com backend WSL2 e containers Linux; iniciar o daemon.
Na raiz do repositório, em PowerShell:

```powershell
docker version
docker build --target cpu -t partner-copilot:cpu .
docker run -d --name partner-copilot -p 127.0.0.1:8000:8000 -v partner-copilot-state:/state -e LLM_BACKEND=fake partner-copilot:cpu
docker logs -f partner-copilot
```

Primeira execução precisa de internet para baixar **apenas o encoder multilíngue**
e indexar `data/splits/rag.jsonl`. Não baixa Mistral. O bootstrap verifica hashes e
separação dos splits, faz upserts determinísticos, verifica cobertura e só então
escreve um marcador atômico no volume. Uma falha não gera marcador de sucesso;
a próxima execução retoma os upserts. O cache e o banco ficam no volume `/state`.
O encoder é liberado ao substituir o processo de bootstrap pelo processo da API;
a API carrega seus próprios recursos uma vez, sem recarga por requisição.

Reinícios com o mesmo volume reutilizam o índice. Mudanças nos dados, modelo ou
parâmetros de chunking exigem outro volume/CHROMA_PATH; não há reset destrutivo
automático. Pesos de embeddings não têm revisão fixada neste projeto: nome e
hashes dos dados fixos não garantem reprodução bit a bit dos pesos/dependências.
A imagem usa faixas de dependências, não um lockfile integral.

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/restaurants
$body = @{ restaurant_id="rest_001"; question="Há reclamações de entrega?"; k=8 } | ConvertTo-Json
Invoke-RestMethod -Method Post http://localhost:8000/ask -ContentType application/json -Body $body
docker inspect --format '{{.State.Health.Status}}' partner-copilot
docker exec partner-copilot id
```

Esperado: health 200 depois da indexação, UID 10001, 8 restaurantes, resposta
rotulada SIMULAÇÃO, abstenção fixa e `llm_called=false`. O fake padrão testa o
contrato HTTP, não a qualidade das respostas. O HEALTHCHECK consulta `/health`
com Python stdlib e considera degradação uma falha. Start period de 600 s pode
precisar de ajuste via `--health-start-period` se o download inicial for lento.
Para verificar reuso, reinicie com `docker restart partner-copilot` e consulte
`docker logs`: deve aparecer `container_index_reused`.

## Configuração e arquivos

Toda configuração é ambiente: configurações Settings/APISettings e API_HOST,
API_PORT (padrões 0.0.0.0 e 8000). Um único worker. CHROMA_PATH, HF_HOME e
API_EMBEDDING_CACHE apontam para `/state`; API_ALLOW_MODEL_DOWNLOAD=true permite
o download inicial. Depois de popular o volume, pode usar false com cache completo.
Dados versionados são somente leitura no diretório da aplicação; volumes montados
devem permitir escrita ao UID/GID 10001. Não iniciar como root para contornar permissões.

`.dockerignore` usa allowlist: exclui `.env`, Git, anexos, relatórios, caches,
Chroma e bytecode do contexto. COPY é explícito. A imagem contém somente código,
configurações públicas, nomes de restaurantes e splits versionados. Os splits
não-RAG são necessários para a checagem de integridade; **apenas rag é indexado**.
Nenhum peso ou banco é copiado ou baixado durante o build. Não usar token em ARG,
Dockerfile ou comando salvo; o encoder público não precisa de HF_TOKEN.

## Replay

Replay usa contexto gravado e **não constrói índice nem carrega encoder**. Monte
um catálogo aprovado e seus artefatos como volume somente leitura, com caminhos
relativos ao catálogo. A validação de hashes, perfil, parser e aprovação humana
continua obrigatória. Não há catálogo aprovado incluído; não inventar aprovações.

```powershell
docker run --rm -p 127.0.0.1:8000:8000 --mount "type=bind,source=C:\caminho\catalogo,target=/recordings,readonly" -e LLM_BACKEND=replay -e API_REPLAY_CATALOG=/recordings/catalog.json partner-copilot:cpu
```

Sem catálogo válido `/health` fica degradado e `/ask` retorna erro próprio; isso
não é uma demo pronta. Ver [contrato da API](api.md) para a curadoria necessária.

## Caminho GPU: não testado localmente

A imagem CPU recusa backend real. Para ele, criar uma imagem **separada**, baseada
por exemplo em `nvidia/cuda:12.8.1-runtime-ubuntu24.04`, com Python compatível,
PyTorch CUDA, bitsandbytes e accelerate; verificar a compatibilidade entre driver,
CUDA, torch e bitsandbytes antes de fixar versões. Instalar o projeto completo.
Essa é uma orientação de implementação, não um Dockerfile GPU validado.

No host Linux com NVIDIA Container Toolkit, uma futura imagem GPU seria executada
com `docker run --gpus device=0 ... -e LLM_BACKEND=real <imagem-gpu>` e volumes
externos para encoder, índice e pesos Mistral. Usar diretamente
`python -m uvicorn partner_copilot.api:app --host 0.0.0.0 --port 8000 --workers 1`,
com bootstrap próprio para o índice; não o entrypoint CPU que recusa real.
Aceite/download do modelo e segredos devem ser externos à imagem. Pesos não devem
ser incluídos em nenhuma camada. Nenhum build, inferência ou comparação FP16 GPU
foi realizado para esta receita.
