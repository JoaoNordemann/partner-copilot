# Prompt e contrato de geração

O template ativo é `src/partner_copilot/generation/templates/partner-copilot-v1.txt`.
Ele não contém exemplos. Nenhuma pergunta do eval set foi copiada para as instruções.
O desenho usa aprendizados anteriores de retrieval, portanto não é um experimento
cego; o manifesto registra essa exposição. Não houve teste de geração real usado
para ajustar este prompt.

## Regras da versão inicial

- Usar somente trechos e metadados fornecidos e exigir evidência explícita da informação
  solicitada. Compartilhar assunto, item ou restaurante não basta.
- Não inferir fatos ausentes nem converter um relato em causalidade, frequência ou tendência.
- Cada linha da resposta normal contém uma afirmação ou recomendação e termina com [review_id].
- Recomendações são opcionais, proporcionais à evidência e identificadas como recomendações.
- Sem suporte, devolver somente `[[SEM_EVIDENCIA]]`, sem citações ou ações.
- A pipeline traduz o marcador para “Não há evidência suficiente nas avaliações fornecidas.”.

O template não exige um número mínimo de recomendações. Na resposta parcial, somente
a parte sustentada pode ser afirmada, com limitação explícita e citações.

## Dados e mensagem de chat

O Mistral recebe uma única mensagem `user`; não acrescentamos uma mensagem `system`.
Isso é verificado no teste do adaptador com loaders falsos. O teste não carrega o
tokenizer ou os pesos reais do Mistral.

Reviews ficam em `<AVALIACOES_JSONL>`, com um objeto JSON por linha. A pergunta fica
em `<PERGUNTA_JSON>` como string JSON. Valores escapam `<`, `>`, `&`, `[` e `]`, além
dos escapes padrão do JSON: um texto não consegue introduzir literalmente um fechamento
de bloco ou [INST] no prompt. Ler o JSON recupera o texto original. Os campos enviados
são review_id, restaurant_id, item, created_at, rating, text e índice/contagem de chunks.
Não enviamos os aspectos anotados ou o score para não oferecer rótulos ou confundir
proximidade com confiança. IDs devem caber na sintaxe de citação alfanumérica, _ ou -.

As instruções declaram esses blocos como dados não confiáveis e rejeitam pedidos de
alteração de regras neles. Delimitar e escapar reduz o risco; não comprova resistência
do modelo a injeção. Os testes verificam a estrutura, não imunidade comportamental.

## Integração à pipeline

`RAGPipeline` agora devolve `Answer` com answer, sources, abstained, abstention_reason
e metadata: latency_ms, retrieved_documents, context_documents, prompt_version e llm_called.

- Sem documentos: frase pública padronizada, fontes vazias, retriever_empty; sem chamada ao LLM.
- Marcador exato após strip(): frase padronizada, fontes vazias, llm_insufficient_evidence.
- Resposta normal: cada linha deve terminar com citações; IDs fora dos documentos
  enviados, respostas vazias, apenas citações ou marcador misturado com texto geram
  `GenerationContractError`. Sources contém só os IDs citados, únicos e na ordem de uso.

A checagem sintática não consegue provar que cada oração é sustentada pelo trecho.
Uma frase incorreta com um ID válido pode passar no validador; a avaliação de geração
precisa detectar esse caso. Uma recusa fora do protocolo não vira abstenção correta
por conveniência. Exceções não são mascaradas como falta de evidência.

A pipeline seleciona até CONTEXT_K=5 documentos, mantendo a ordem do retriever.
RETRIEVAL_K continua 8, com o limiar atual. No Mistral, o tamanho tokenizado do prompt
mais o orçamento de geração deve caber na janela do modelo e do tokenizer. Se não
couber, há erro explícito antes de generate, sem truncar os trechos silenciosamente.

## Versionamento

`templates/manifest.json` registra versão, arquivo, SHA256 canônico e formato de dados.
O carregamento confere o hash. O teste de snapshot também congela a renderização
com uma pergunta e uma review sintéticas que não vêm do eval set.
`legacy-v0.txt` preserva o template anterior e não pode ser selecionado para inferência.

Depois de avaliar v1, qualquer ajuste das instruções ou do formato de contexto/saída
exige uma nova versão, por exemplo partner-copilot-v2, novo template/hash e snapshot.
Preserve v1 e registre o que motivou a mudança. Cada relatório de geração deverá
registrar o prompt_version/hash e a configuração usada. Alterar somente o arquivo
ou o manifesto antigo para fazer o teste passar quebra esta política.

## Executar os testes

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_generation_prompt.py tests/test_retriever.py tests/test_retriever_dependencies.py -v
.\.venv\Scripts\python.exe -m pytest tests/test_configuration_integration.py -v
```

O primeiro grupo usa dependências leves; o segundo testa o adaptador com mocks e a
biblioteca Torch instalada, sem baixar modelo. O workflow de CI inclui o primeiro grupo.
O empacotamento também foi verificado com um wheel local, que contém todos os templates.

A validação ponta a ponta com Mistral-7B real continua pendente, inclusive os quatro
negativos q25–q28. Testes unitários não permitem reportar sua taxa de abstenção real.

A consulta agora tem entrada ask e erro específico InvalidCitationError, com IDs e ocorrências inválidas contáveis. A resposta inteira é rejeitada; não há remoção silenciosa. O template v1 e seu hash não mudaram. [CLI e política de validação](ask-cli.md).
