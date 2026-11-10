# Decisões de schema e metadados

## Data: ISO na origem, inteiro para filtros

`Review.created_at` é `date`, lido e serializado como ISO (`2026-11-01`).
`Review.created_at_int` é calculado dessa data como inteiro `YYYYMMDD` (`20261101`).
Não há conversão de fuso: a granularidade dos dados é diária. Não usamos epoch.

O Chroma recebe ambos os campos. Filtros `$gte` e `$lte` usam **created_at_int**;
`created_at` preserva a data legível e permite reconstruir o schema.
O valor inteiro é sempre derivado, evitando datas contraditórias na ingestão.

```python
where = {
    "$and": [
        {"created_at_int": {"$gte": 20261019}},
        {"created_at_int": {"$lte": 20261101}},
    ]
}
```

## Categoria e bairro

`category` e `bairro` são strings obrigatórias e não vazias em `Review`.
Ambas são persistidas como metadados e preservadas na recuperação.
Isso permite filtros exatos por categoria e bairro, combinados com restaurante e data.
Os valores são preservados como recebidos, incluindo acentos; não há normalização implícita.

## Aspectos e ausência

`Review.aspects` é um mapa de nomes de aspectos para `"pos"` ou `"neg"`.
Aspecto não mencionado **não existe no mapa nem como chave aspect_<nome> no Chroma**.
Não usamos `"none"`, string vazia ou null persistido como uma terceira polaridade.

Exemplo: `{"sabor": "pos"}` produz `aspect_sabor="pos"` e nenhuma chave
`aspect_tempo_entrega`. `aspects_json` guarda o mapa completo como JSON para
reconstrução; os filtros usam as chaves escalares `aspect_<nome>`.

O Chroma mescla metadados no upsert. Para remover um aspecto antes mencionado,
o store envia `None` como instrução de exclusão da chave antiga; a chave fica ausente
no documento persistido. Esse comportamento foi verificado no ChromaDB 1.5.9,
agora a versão mínima declarada. Novo upsert também remove sentinelas de índices antigos.

Testes verificam filtros combinados, derivação da data, rejeição de polaridades inválidas,
recuperação do mapa e ausência real de chaves após atualização e reabertura da coleção.

Parâmetros e integridade do dataset estão em [decisions.md](../decisions.md).

## Contrato dos embeddings

O modelo é definido por `EMBEDDING_MODEL`, com MiniLM multilíngue como padrão.
Documentos e consultas usam a interface do embedder em `ingestion/embedder.py`, com
normalização L2 e vetores explícitos no Chroma. O modo E5 aplica `passage: ` nos documentos
e `query: ` nas consultas. A coleção registra esse pré-processamento para impedir mistura
de vetores incompatíveis. Trocar modelo ou prefixos exige outra coleção, mesmo com a mesma
dimensão; batching e dispositivo são configurações de execução. Detalhes em
[embeddings.md](embeddings.md).

## Store persistente e cidade

A persistência é implementada em `ingestion/chroma_store.py`, com alias do import anterior.
O nome automático combina o prefixo configurado, o modelo e um hash do contrato dos vetores;
o nome literal explícito continua disponível para abrir collections existentes.
`reset()` limpa somente os documentos da collection alvo, sem reset global do cliente.

`city` é opcional no `Review` e nos metadados: cidade desconhecida significa chave ausente.
Não inferimos cidade por bairro nem alteramos os dados brutos para preencher esse campo.
Os demais metadados filtráveis permanecem escalares; `created_at_int` continua YYYYMMDD.
Detalhes e exemplos em [chroma-store.md](chroma-store.md).

## Contrato de retrieval

Score de cosseno, limiar inclusivo, filtros temporais e abstenção estão definidos em [retriever-contract.md](retriever-contract.md).

## Conjunto de avaliação de retrieval

As 30 perguntas usam um corpus gold isolado, filtros estruturais sem rótulos de aspecto e relevâncias congeladas. As anotações são provisórias de IA, pendentes de revisão humana independente. Janelas temporais são fixas em 01/11/2026. O conjunto serve para desenvolvimento e calibração; não é teste final após ajuste de limiar. Protocolo, auditoria e baseline nos dois modos: [retrieval-evaluation.md](retrieval-evaluation.md).

## Métricas e baselines de ranking — protocolo definido antes do cálculo

Para cada pergunta respondível, R é o conjunto de IDs relevantes congelados e L_k
é o prefixo de até k IDs distintos retornados. H = |R ∩ L_k|. Reportaremos k = 1, 3, 5, 8.
As médias são macro nas 24 perguntas respondíveis, com o mesmo peso por pergunta.

- hit@k = 1 se H > 0; caso contrário, 0.
- recall@k limitado = H / min(k, |R|). Esta é a definição solicitada para o novo
  relatório; o recall clássico H / |R| continuará separado e identificado, sem
  reinterpretar o baseline anterior. O recall limitado também é chamado capped recall.
- MRR@k = média de 1/r, sendo r a posição do primeiro relevante até k;
  vale zero quando não há relevante no prefixo.
- precision@k = H / k. Posições não preenchidas contam como zero, inclusive se os
  filtros deixarem menos de k candidatos. Não dividimos pela quantidade retornada.

As seis perguntas sem resposta não entram nessas quatro médias, pois R é vazio.
Reportamos para elas a taxa de abstenção correta e a taxa de falsa aceitação de
qualquer evidência. Também reportamos abstenção nas perguntas respondíveis.

Comparação principal: ranking sem corte por score para todos os métodos, nos modos
sem filtro e com os mesmos filtros estruturais de restaurante/item/data. O aleatório
usa permutações uniformes sem reposição do mesmo conjunto elegível: 200 repetições,
seeds 42..241, média e desvio padrão entre repetições. Uma permutação por pergunta e
seed é reutilizada nos quatro k, sem alterar o estado aleatório ao mudar k.
Filtros muito restritivos podem tornar o aleatório forte; não interpretaremos todo
ganho sobre esse piso como qualidade semântica ou exigiremos uma margem impossível.

O baseline lexical usa contagem de termos distintos compartilhados após casefold,
remoção de acentos, tokenização alfanumérica e exclusão de uma lista fixa de palavras
funcionais pt-BR, declarada no código antes da execução. Não usa stemming, sinônimos,
labels ou expansão de consulta. Empates são resolvidos por ID, inclusive score zero.
Embeddings e lexical recebem somente o texto das reviews. Relevâncias nunca entram
na geração dos rankings ou nas pontuações.

A comparação operacional fica separada: embedding com min_score=0.25 (sem ajuste),
lexical com score > 0 e aleatório sem limiar (não há confiança semântica no acaso).
Esses cortes não são probabilidades equivalentes. A tabela principal sem limiar
isola ranking; a operacional mostra o efeito de rejeitar evidência. Não haverá
calibração de limiar neste cálculo nem uso deste conjunto como teste final.

Coleções históricas de embedding em inglês serão inspecionadas sem modificações.
Uma ablação comparável exige os mesmos 100 documentos, texto e pré-processamento;
vetores de outro corpus não serão comparados como se fossem o mesmo experimento.
Se o modelo inglês histórico estiver disponível em cache, poderá ser reembutido
no banco isolado do mesmo corpus, registrando a origem e a revisão. Na ausência de
coleção histórica elegível, essa ablação será explicitamente marcada como não executada.

## Calibração de min_score — protocolo anterior à seleção do limiar

Fixamos k=8 e usamos o maior score de cosseno exato registrado em
reports/retrieval-comparison.json, sem aplicar previamente o corte 0.25.
O modo principal é com filtros; o mesmo limiar será aplicado ao modo sem filtro,
sem selecionar um segundo limiar nos seus resultados. Sem candidato significa
score ausente (null), não zero; sempre abstemos nesse caso.

Partição determinística por hash SHA256 de "20261103:<id>", estratificada:
calibração 20 perguntas (5 restaurante/aspecto, 3 temporais, 3 por item, 5 paráfrases,
3 negativas semânticas e 1 negativa estrutural); avaliação 10 (as restantes).
Isso dá 16 respondíveis + 4 sem resposta na calibração e 8 + 2 na avaliação.
As negativas estruturais são item inexistente/janela vazia; não são misturadas com
as semânticas na descrição dos erros. A partição não consulta scores.

Escolha: maximizar balanced accuracy na calibração, isto é, média entre a fração
de respondíveis aceitas e a fração de sem resposta corretamente rejeitadas.
Usamos a grade fixa 0.000..1.000, passo 0.001; aceitação inclusiva score >= limiar.
Empates: menos falsas aceitações de perguntas sem resposta; depois menor limiar.
A escolha usa somente as 20 perguntas. Não ajustamos k, grade ou função de custo
após observar o resultado. Comparamos também o limiar anterior 0.25.

Registrar score máximo e ID do primeiro documento para as 30 perguntas nos dois
modos, inclusive se o documento é irrelevante. Aceitar uma pergunta respondível
não prova que recuperou evidência válida: reportaremos separadamente se há ao menos
um relevante nos oito documentos que passaram pelo corte.
Distribuições: contagens, mínimo, quartis, mediana e máximo por grupo; scores ausentes
são contados separadamente. Overlap numérico dos intervalos não prova separabilidade;
mostraremos exemplos concretos de negativas com score maior que positivas.

Limitação essencial: as 30 perguntas já foram usadas nos baselines e lidas por IA.
Esta divisão impede usar as dez perguntas nesta nova otimização, mas não as torna
um teste final independente ou nunca observado. Reportaremos contagens e essa
exposição anterior; as anotações gold continuam pendentes de revisão humana.
O limiar escolhido é experimental e será registrado em artefato próprio. Não será
promovido automaticamente ao default global nem sobrescreverá o .env local sem
validação em perguntas novas. O relatório deve mostrar o custo, mesmo quando ruim.

Resultado da seleção: candidato experimental 0,287, sem promoção ao default. Na avaliação separada, rejeitou 1/2 sem resposta (igual a 0,25) e preservou evidência em 7/8 respondíveis (antes 8/8). Sobreposição e exposição histórica impedem tratar isso como ganho validado. Relatório: [min-score-calibration.md](min-score-calibration.md).

## Testes unitários e análise de falhas

O núcleo do retriever não importa Chroma nem frameworks de modelos. Testes com store falso e bloqueio de dependências pesadas rodam em workflow mínimo; os testes de integração permanecem separados. As cinco piores perguntas do baseline operacional são selecionadas por perda, MRR e ID, sem mudar julgamentos para melhorar métricas. Diagnósticos e fontes: [retrieval-failure-analysis.md](retrieval-failure-analysis.md).

## Revisão dos resultados e limites de evidência

Contagem operacional com filtros e corte 0,25: 4/6 sem resposta retornam documentos; 1/24 respondíveis tem recall@8 zero. Os cinco casos selecionados cobrem todas as perdas máximas. O filtro não recalibra scores; confusão temática é hipótese, e a inversão observada prova que um limiar único não separa todos os exemplos. Dez inspeções textuais de IA identificadas, revisão humana pendente. CI remoto de f31831b confirmado como success. Tabelas, proveniência e experimentos de geração/segmentação registrados em [retrieval-checkpoint.md](retrieval-checkpoint.md).

## Revisão humana assistida e versão dos julgamentos

Revisão no chat concluída em 15 perguntas e 56 pares apresentados, após exposição aos resultados e com esclarecimentos da IA. Não é revisão cega independente nem exaustiva do corpus. Human-v2 preserva v1 e registra uma alteração: rev_002800 relevante em q22 por decisão do responsável, sem mudar o gold ABSA ou a regra global para diferente do habitual. Rankings e scores são reutilizados somente após validar corpus, perguntas e filtros idênticos; métricas e aleatório são recalculados. O default histórico e o limiar 0,25 permanecem. Protocolo e resultados: [human-review-results.md](human-review-results.md).

## Reexecução sem filtros na versão humana v2

Nova execução usa 100 candidatos para todas as perguntas no modo sem filtro, sem restrições de restaurante, item ou data. Em k=8 sem corte, Hit é 12/24 sem filtro contra 24/24 com filtro; com min_score=0,25, o filtrado cai para 23/24. O ganho não é uma medida causal isolada do embedding: filtros fornecem escopo ausente do texto. Resultados e reprodução: [unfiltered-retrieval-check.md](unfiltered-retrieval-check.md).

## Baselines baratos executáveis sem modelo

Comando dedicado mede aleatório (200 repetições, seeds 42..241) e contagem de palavras normalizadas, sem carregar embeddings ou Chroma. Na revisão human-v2, com filtros, Hit@8 é 0,9315 aleatório, 23/24 lexical e 24/24 semântico. Hit@8 sozinho é pouco discriminante nesse conjunto filtrado; considerar Hit@1, MRR e precision. Sem filtros, lexical e semântico empatam em Hit@8, e o lexical vence em recall limitado@8. Resultados completos: [cheap-baselines-check.md](cheap-baselines-check.md).

## Versão ativa de avaliação

DATA_EVAL_DIR passa a usar data/eval/human-v2 por padrão no config e no exemplo de ambiente. O v1 permanece congelado e só deve ser selecionado explicitamente com --eval-dir data/eval. O recálculo exige --parent-eval-dir para distinguir a versão de origem da versão revisada. Valores explícitos de ambiente/.env mantêm sua precedência e devem ser atualizados quando apontarem para v1.

## Contrato de resposta, abstenção e contexto da geração

Status: decisões registradas antes da implementação no commit 04d67de. O prompt v1,
o retorno estruturado, os dois caminhos de abstenção e a seleção de contexto agora
estão implementados e cobertos por testes com doubles. A taxa de abstenção e a
fidelidade com o Mistral real ainda precisam de avaliação; os testes de formato não
certificam a qualidade semântica da geração.

### Saída pública do pipeline

O pipeline devolverá um modelo Pydantic serializável com:

| Campo | Tipo | Significado |
| --- | --- | --- |
| answer | str | Resposta ao usuário ou a frase padronizada de abstenção. |
| sources | list[str] | IDs únicos de reviews efetivamente citadas na resposta, na ordem da primeira citação. |
| abstained | bool | True somente quando o pipeline se abstém por falta de evidência. |
| abstention_reason | retriever_empty / llm_insufficient_evidence / null | Origem da abstenção; null em respostas normais. |
| metadata.latency_ms | float >= 0 | Tempo total da chamada ask, medido com relógio monotônico de alta resolução. |
| metadata.retrieved_documents | int >= 0 | Quantidade devolvida pelo retriever após filtros, min_score e limite retrieval_k. |
| metadata.context_documents | int >= 0 | Quantidade de documentos/chunks efetivamente enviada ao LLM após a seleção do contexto. |
| metadata.prompt_version | str | Identificador do template configurado; versão inicial partner-copilot-v1. |
| metadata.llm_called | bool | Indica se a geração foi chamada, permitindo distinguir os dois caminhos. |

A latência começa na entrada de ask e termina após validar e montar o resultado.
Inclui retrieval, preparação do prompt, geração e validação; inclui carregamento
preguiçoso se ocorrer nessa chamada. Não inclui transporte HTTP ou fila externa.
As contagens são de documentos/chunks, não de IDs distintos de reviews.
No caminho sem chamada ao LLM, context_documents=0 e llm_called=false; prompt_version
continua identificando o template configurado, sem afirmar que ele foi executado.

sources não é a lista inteira de documentos recuperados. As citações usam [review_id]
e só podem referenciar reviews presentes no contexto enviado. O pipeline extrairá
os IDs citados, validará sua pertença ao contexto e removerá repetições. Não poderá
aceitar uma resposta normal sem citação nem devolver IDs inventados. Validar um ID
não prova que a afirmação está sustentada: fidelidade exige avaliação de geração.
Em qualquer abstenção, sources=[] e abstention_reason é obrigatório; em resposta
normal, abstained=false e abstention_reason=null.

Exemplo de resposta normal (valores ilustrativos, não resultado de inferência):

```json
{
  "answer": "Há relato de espera além do prazo combinado [rev_000212].",
  "sources": ["rev_000212"],
  "abstained": false,
  "abstention_reason": null,
  "metadata": {
    "latency_ms": 1250.0,
    "retrieved_documents": 8,
    "context_documents": 5,
    "prompt_version": "partner-copilot-v1",
    "llm_called": true
  }
}
```

### Abstenção explícita e detectável

Marcador interno único que o LLM deverá emitir, sozinho e sem citações ou recomendações:

```text
[[SEM_EVIDENCIA]]
```

A detecção é igualdade da saída completa após strip(), não busca por substring.
Isso permite apenas whitespace externo; marcador junto de explicações, citações,
Markdown ou resposta vazia não satisfaz o formato. A instrução vale quando os textos
não sustentam a informação específica pedida, mesmo que tratem do mesmo assunto,
item ou restaurante. Não inferir receita, alergia, reembolso ou contaminação a partir
de avaliações genéricas. Havendo evidência apenas parcial, responder somente à parte
sustentada, citando-a e explicitando a limitação, sem inventar a parte ausente.

Ao reconhecer o marcador, o pipeline devolverá ao usuário exatamente:

```text
Não há evidência suficiente nas avaliações fornecidas.
```

O marcador é protocolo interno, não texto a exibir. Os dois caminhos usam essa mesma
frase pública. A saída pública sempre inclui abstained e abstention_reason; métricas
e testes não procurarão sinônimos de recusa no texto final.

Exemplo do caminho de recusa pelo LLM:

```json
{
  "answer": "Não há evidência suficiente nas avaliações fornecidas.",
  "sources": [],
  "abstained": true,
  "abstention_reason": "llm_insufficient_evidence",
  "metadata": {
    "latency_ms": 1250.0,
    "retrieved_documents": 8,
    "context_documents": 5,
    "prompt_version": "partner-copilot-v1",
    "llm_called": true
  }
}
```

Solicitar um marcador no prompt não garante obediência. Saída vazia, recusa livre sem
o marcador e sem citações válidas, mistura do marcador com outros textos ou citações
fora do contexto serão erros explícitos de contrato da geração, não abstention_reason
adicionais nem respostas normais silenciosas. Exceções de execução também não serão
mascaradas como falta de evidência. O tratamento HTTP desses erros será definido na
camada de API; esta decisão não fixa status HTTP nem política de retry.

### Dois caminhos distintos

1. Retriever devolve []: retornar imediatamente a frase pública, sources=[],
   abstained=true, abstention_reason=retriever_empty, retrieved_documents=0,
   context_documents=0 e llm_called=false. Nenhuma inferência é executada.
2. Retriever devolve documentos, mas o LLM emite [[SEM_EVIDENCIA]]: retornar a mesma
   frase pública, sources=[], abstained=true,
   abstention_reason=llm_insufficient_evidence e llm_called=true. Preservar as contagens
   reais de documentos recuperados e enviados, mesmo com sources vazio.

A segunda condição precisa ser avaliada explicitamente: no baseline operacional,
4/6 perguntas sem resposta (q25–q28) ainda recebem documentos. Lista não vazia não
é evidência suficiente. Esses quatro casos devem entrar no teste de geração ponta
a ponta. Registrar separadamente abstenções por retrieval vazio, recusas do LLM,
falsas respostas e violações de formato; reportar contagens e o número de tentativas.
Não excluir violações de formato do relatório como se fossem respostas bem-sucedidas.
A medição de abstenção do LLM deve distinguir chamadas de geração de recusas anteriores
à inferência, para não atribuir ao Mistral o acerto de um filtro sem candidatos.

### Tamanho inicial do contexto

Fixar context_k=5, configurável e separado de retrieval_k=8. O retriever mantém
min_score=0,25, filtros e sua política atual de 2*k candidatos antes do corte.
A geração seleciona os primeiros min(context_k, len(docs)) documentos devolvidos,
preservando a ordem de similaridade. Não relaxar filtro ou limiar para completar
cinco documentos, nem usar documentos que não passaram no retriever.
A seleção inicial não adiciona reranking nem deduplicação por review; contagens
referem-se a documentos/chunks. A implementação deverá verificar a janela de tokens
antes da inferência e falhar explicitamente se o prompt exceder o limite, evitando
truncamento silencioso da evidência. Uma política de orçamento/adaptação de contexto
poderá ser decidida depois de medir esses casos.

Justificativa: no ranking sem corte com filtros de human-v2, Hit@5=23/24 e
Hit@8=24/24; precision@8=0,276. O acaso com filtros já alcança Hit@8 médio de 0,931.
Esses números não demonstram que cinco documentos geram respostas melhores: são
motivação para começar com menos contexto e medir. Não confundir essas métricas
sem corte com o comportamento operacional após min_score.
Comparar context_k=3,5,8 posteriormente, mantendo modelo, filtros, limiar e template
fixos entre variantes. Medir suporte factual, citações, abstenção, latência e tamanho
do prompt; não escolher context_k somente pelo Hit de retrieval. O conjunto já foi
exposto e revisado com assistência; ganhos obtidos ajustando nele não serão tratados
como teste final independente.

### Versão do prompt e verificações da implementação

A versão partner-copilot-v1 identifica o primeiro template que implementar este
contrato. Alterações de instrução, formato ou serialização do contexto exigem nova
versão. O snapshot completo do prompt usado em uma avaliação deve ser recuperável
pelo código versionado; o identificador sozinho não substitui esse registro.

Antes de considerar a implementação concluída, verificar com doubles de retriever
LLM: saída normal com fontes válidas; ambos os caminhos de abstenção; ausência de
chamada ao LLM com retrieval vazio; marcador exato e violações de formato; contagens,
latência não negativa e versão; no máximo cinco documentos no prompt; respostas com
citações somente de reviews enviadas. O teste com o modelo real é separado dos
unitários de CI e deve informar o comportamento observado nos quatro negativos.


## Prompt de evidência explícita: primeira versão implementada

A versão partner-copilot-v1 usa somente role=user no chat template. O template
legado foi arquivado como legacy-v0; ele não pode ser selecionado para novas chamadas.
V1 não tem exemplos nem perguntas copiadas do eval set. Foi desenhado após conhecer
os resultados de retrieval, e essa exposição está declarada no manifesto do prompt.
Nenhuma avaliação de geração com o Mistral real foi usada para ajustar esta versão.

Cada review vira um objeto JSONL delimitado, sem labels de aspectos ou scores de
similaridade. Tags de delimitadores e marcadores de chat em valores de dados são
escapados; os textos continuam decodificáveis como JSON. Isso reduz ambiguidade e
risco de injeção, sem garantir que o modelo ignorará instruções maliciosas.

O template exige suporte explícito ao fato, uma afirmação/recomendação por linha
com fonte, ações apenas quando motivadas por evidência e o marcador exato quando não
houver suporte. A pipeline normaliza esse marcador para a frase pública já definida,
registra abstention_reason e devolve apenas IDs citados que existam no contexto.
A validação cobre formato e pertença das fontes; não comprova fidelidade factual.

CONTEXT_K=5 e PROMPT_VERSION=partner-copilot-v1 são configuráveis. O adaptador do
Mistral valida prompt + orçamento de geração contra a janela real sem truncamento
silencioso. O workflow de testes unitários passa a incluir o contrato do prompt,
sem carregar modelos. O wheel inclui os templates e seu manifesto.

O hash do template e o snapshot renderizado ficam congelados. Toda alteração de
instruções, formato de resposta ou serialização do contexto após observar resultados
exige versão nova e preservação da anterior; não substituir v1 silenciosamente.
A avaliação futura deverá registrar versão/hash, parâmetros de geração e violações
de formato, inclusive nos quatro negativos q25–q28. Protocolo e limites em
[prompt-design.md](prompt-design.md).

## Execução reprodutível e instrumentada do Mistral

Provider lazy por processo, protegido por lock, evita carregar pesos por pergunta e rejeita troca de configuração após a primeira carga. Modelo em eval; compute_dtype bf16 apenas se as GPUs visíveis suportarem, com fallback fp16. Seed 42 reiniciada por chamada com restauração do RNG; temperatura padrão 0 para greedy, mantendo amostragem coerente quando configurada positiva. Prompt, chat template e tokens especiais continuam no protocolo v1, sem alteração das instruções.

Validar tokens reais do prompt + reserva max_new_tokens + margem configurável de 256 contra a janela efetiva, sem truncamento. GenerationResult leva métricas por chamada; a pipeline as inclui em metadata.generation, preservando generate()->str. Sincronizar CUDA e reiniciar picos por chamada; registrar bytes alocados/reservados por GPU, baseline residente, latência de geração e tempo da carga única. Inferência serializada para evitar corrida do RNG/contadores; medidas não garantem isolamento de outro trabalho CUDA no processo. Ambiente local sem GPU: validação com doubles, sem benchmark real anunciado. Detalhes: [generation-runtime.md](generation-runtime.md).

## CLI ask e falhas de citação

Decisão anterior à implementação desta entrada: toda citação deve referenciar uma
review realmente enviada ao LLM. Isso é mais estrito que pertencer ao conjunto
recuperado, porque documentos além de CONTEXT_K não foram vistos pelo modelo.
Uma citação desconhecida invalida a resposta inteira: não remover o ID nem publicar
o restante do texto. Não transformar erro de citação em abstenção por falta de evidência.

A falha será InvalidCitationError, subtipo de GenerationContractError, com código
estável invalid_citation, IDs inválidos únicos, contagem de ocorrências inválidas e
IDs permitidos no contexto. Falhas de formato permanecem separadas. Um ID válido
não comprova que a afirmação está apoiada na fonte; isso depende da avaliação de geração.

A CLI ask exibirá resposta, fontes, abstenção e metadados, com modo --json. Saídas
JSON de sucesso ou erro vão para stdout; logs vão para stderr. Erros de sintaxe dos
argumentos continuam no padrão argparse (stderr). Códigos de saída: 0 para resposta
ou abstenção válida; 2 para configuração/preflight; 3 para citação inválida; 4 para
outra violação do contrato de geração; 1 para falha de execução. Conte ocorrências
invalid_citation para respostas rejeitadas e invalid_citation_count para referências
inválidas, inclusive repetidas; não confundir as duas unidades.

A entrada só abre uma collection existente e valida seus IDs contra o split RAG
registrado, preservando a separação de treino/gold. Não cria índice vazio quando o
nome/modelo está errado, nem ingere/reset a base. Coleção existente sem resultados
leva à abstenção normal sem carregar o LLM. Datasets de avaliação isolados continuam
sendo responsabilidade dos seus runners, não desta CLI de consulta de produção.

## Testes sem GPU e teste real separado

O grupo leve testa a pipeline com retriever/LLM falsos e confirma explicitamente ausência de chamada com lista vazia, instruções/IDs no prompt enviado, erro contável para fontes fora do retrieval/contexto e normalização do marcador para a frase pública de abstenção. Texto livre não é contado silenciosamente como recusa válida.

Testes reais de Mistral ficam marcados gpu e desabilitados por padrão via --run-gpu; CI seleciona arquivos leves e -m not gpu. Dois casos sintéticos usam pesos reais em cache, uma carga por módulo, seed fixa e temperatura zero; loaders proíbem download. Ambiente sem CUDA é skip explícito, não aprovação de inferência real. Protocolo: [testing.md](testing.md).

## Rodada completa de geração com checkpoint por pergunta

A rodada usa as 30 perguntas e o corpus gold isolado de human-v2, com configuração
fixa de retrieval/contexto/geração e prompt versionado. Nunca misturar o gold no índice
RAG de produção. A execução real exige CUDA; doubles só podem produzir artefatos
explicitamente identificados como teste, sem serem publicados como resultados do Mistral.

Salvar um JSONL de resultados com uma linha por pergunta, incluindo pergunta/filtros,
IDs, scores e textos recuperados/enviados, prompt renderizado, versão/hash, saída bruta,
Answer ou erro, latência e métricas de geração. Flush e fsync a cada pergunta; manter
lock de escrita. Retomada explícita só aceita o mesmo snapshot, template, parâmetros
e ambiente registrados, pula perguntas já gravadas e preserva erros como tentativas
concluídas. Recuperar somente uma cauda final interrompida, arquivando-a; corrupção
no meio e IDs duplicados devem impedir a retomada.

Métricas antes da execução: abstenções válidas nas 6 negativas, com contagem separada
q25–q28 e dos motivos retriever_empty/llm_insufficient_evidence; abstenções nas 24
respondíveis; erros separados, nunca tratados como abstenção correta. Taxas finais
só com as 30 tentativas registradas. Reportar sempre numerador/denominador e erros.

Validade de citações é calculada na saída bruta não abstida do LLM: exige ao menos
uma citação e todos os IDs no contexto realmente enviado. Respostas sem citações
contam como inválidas; abstenções com marcador exato e casos sem chamada ao LLM ficam
fora desse denominador. Essa métrica de referências é separada da validade de formato
ou da fidelidade factual; erros não são removidos silenciosamente do relatório.

A leitura qualitativa será preparada para q25–q30 e q01/q09/q13/q22: dez perguntas
fixadas antes da geração, incluindo todas as negativas. O relatório de leitura nasce
pendente; gerar um checklist não significa que respostas do modelo foram lidas ou
revisadas por uma pessoa. Respostas reais ainda dependem do ambiente com GPU.


## Versoes independentes de prompt e parser

Decisao anterior a implementacao: preservar o template e o comportamento do parser v1.
PROMPT_VERSION e PARSER_VERSION sao eixos independentes, ambos com default v1.
Prompt partner-copilot-v2 sera uma instrucao mais curta, em portugues, com um exemplo
inventado e regra de saida ao final. Parser parser-v2 normalizara apenas barra
invertida seguida de underscore antes de aplicar as mesmas validacoes estritas de v1.
Nao relaxar abstencao, remover citacoes, alterar evidencias ou adicionar retry nesta etapa.

Registrar versao e hash do parser no experimento e versao na resposta, inclusive
abstencoes sem LLM. Identidades novas de avaliacao usam schema_version 2; checkpoints
antigos ficam preservados e nao podem ser retomados como um experimento novo.
Preservar os hashes dos templates existentes; registrar hashes dos parsers congelados.
Uma alteracao de comportamento exige uma nova versao. Registrar no README:
v2 foi criada depois de ver a v1 nas mesmas 30 perguntas. Nao e avaliacao independente.
Comparacoes: prompt v1/parser v1, prompt v1/parser v2, prompt v2/parser v1 e prompt v2/parser v2.
Nenhuma nova rodada ou resultado de GPU sera anunciado sem execucao real.


## Diagnostico de abstencao e experimento corretivo D

Decisao anterior a implementacao: nao alterar prompt-v2, parser-v1 ou parser-v2.
Metricas novas sao diagnosticas sobre texto bruto: estrita exige saida inteira
igual ao marcador apos strip; tolerante exige marcador literal presente e nenhuma
citacao sintaticamente valida cujo ID exista no contexto. Reportar tambem a mesma
analise apos normalizar underscores, como visao separada e declarada. A tolerante
nao autoriza aceitar respostas na pipeline e nao comprova ausencia de alucinacao.
Abstencoes sem LLM sao contabilizadas separadamente e nas taxas de pipeline.

D sera experimento separado: reutilizar a primeira saida bruta de B e revalidar
com parser-v2 (baseline C), sem nova busca e sem gerar a primeira resposta novamente.
So se a validacao falhar, permitir UMA chamada corretiva, com o erro e a saida anterior
como dado delimitado/escapado. Prompt corretivo tem versao e hash proprios. Validar
a correcao com o mesmo parser. Preservar cada tentativa em checkpoint duravel antes
de prosseguir, inclusive a primeira antes da chamada corretiva. Na retomada, uma
chamada sem resultado salvo fica indeterminada e nao e repetida automaticamente.
Registrar latencia e VRAM da nova chamada separadas das metricas originais de B.
Falhas de runtime nao disparam retry de contrato. Nenhum resultado real de D sem GPU.


## Resultado negativo D e saida estruturada

D nao recuperou nenhuma das 25 rejeicoes de C: 25 chamadas corretivas adicionais,
aceitacao mantida em 2/27. Retry descartado para a pipeline; o runner D permanece
apenas como artefato experimental historico, sem integracao no fluxo normal.
Aderencia a instrucoes e formato e hipotese de gargalo, nao causalidade isolada;
comprimento de prompt nao foi isolado em ablacao. q23 passa parser e nao responde
sobre mensagens ignoradas: manter aceita_pelo_parser e sustentada_para_pergunta
como dimensoes separadas, com leitura explicita para a segunda.

Nova estrategia: partner-copilot-json-v1 + parser-json-v1, sem alterar v1/v2.
Saida JSON estrita: abstem bool; afirmacoes lista de texto e review_ids. Extra fields,
chaves duplicadas, NaN, tipos coercivos, abstencao com afirmacoes ou resposta sem
fontes sao rejeitados. A schema e validada separadamente da pertinencia dos IDs.
O codigo renderiza as referencias. Nao ha retry nem normalizacao silenciosa JSON.
Quatro medidas: schema valido, abstencao correta, IDs no contexto e sustentacao
factual (leitura qualitativa, pendente ate ser realizada).

Criar dez perguntas novas, tres negativas, com corpus e rotulos congelados antes
da primeira inferencia. Nao executar o novo prompt nas 30 antigas. As novas perguntas
usam corpus ja conhecido e rotulos definidos por IA a partir do texto; sao checagem
adicional, nao holdout independente de documentos nem gold humano. Congelar a
primeira versao do prompt antes da criacao das perguntas. Nenhum resultado de GPU
sera anunciado antes da execucao. Timebox maximo de duas horas para esta etapa.


## V3 congelada: JSON com trecho literal e primeiro objeto

Preservar versoes anteriores. partner-copilot-v3 e parser-v3 sao novos registros.
A consistencia estrutural abstem == (afirmacoes vazias) ja existe e sera mantida;
ela nao detecta n10 quando a propria afirmacao diz ausencia mas abstem=false.
Nao converter flags por heuristica textual. Sem resposta, o modelo deve produzir
abstem=true e afirmacoes=[]; coerencia semantica segue sujeita a leitura.

Parser v3 exige que o texto comece com objeto JSON (apos whitespace), usa raw_decode
para o primeiro objeto completo e ignora sufixo, registrando bytes/caracteres
ignorados e preservando a saida bruta. Nao usar stop em } porque objetos aninhados
seriam cortados. Chaves duplicadas e tipos/constantes invalidos seguem rejeitados.
Cada afirmacao traz fontes [{review_id, trecho}]. Cada ID deve estar no contexto,
e cada trecho nao vazio deve aparecer literalmente na review correspondente.
Nao normalizar o trecho, acentos ou espacos. O teste verifica a existencia do
excerto, nao entailment entre excerto e afirmacao, nem relevancia para a pergunta.
Um trecho irrelevante real ainda pode sustentar uma afirmacao inventada no parser;
nao declarar que a regra elimina automaticamente n09.

Contexto v3: ate 8 reviews; retrieval_k=8, min_score=0.25, seed=42, temperatura=0,
max_new_tokens=512 para acomodar JSON com trechos. Mudanca conjunta de prompt,
parser, contexto e reserva de geracao: nao e ablacao causal isolada. A janela
32768 nao estava esgotada: B mediu 711-1236 tokens e JSON v1 638-1020; 1550 nao
e uma medida fixa de instrucoes. Registrar contagens reais por pergunta.

Congelar prompt/parser antes de criar n11-n20 (3 negativas). Nao executar inferencia
exploratoria nem ajustar usando n11-n20; testes de geracao usam fixtures inventadas.
Mesma base conhecida e rotulos por IA: checagem nova de perguntas, nao gold humano
cego ou holdout de documentos. Execucao final: primeiro novas, depois as 30 originais
marcadas contaminadas, mesma instancia de modelo, arquivos distintos, sem retry.


## Protocolo prospectivo de ablações e comparação pareada — 2026-11-06

Registro anterior a qualquer novo cálculo ou execução desta etapa. Resultados
históricos permanecem históricos; este protocolo não os torna pré-registrados nem
apaga a exposição às perguntas. Nenhuma métrica nova foi calculada para este registro.

### Uso permitido das perguntas e exposição

| Conjunto | Exposição já ocorrida | Uso e identificação obrigatória |
| --- | --- | --- |
| q01–q30, human-v2 | Iterações de prompt, análise de falhas e calibração de limiar | Retrieval: benchmark de desenvolvimento exposto. Geração: contaminado. |
| n01–n10 | Iterações de geração, prompt e parser | Geração: contaminado; não usar como confirmação independente. |
| n11–n20 | Uma execução final da configuração v3 congelada; resultados agora conhecidos | A execução histórica pode ser identificada como limpo quanto a ajuste prévio nessas perguntas. Qualquer variante ajustada após a leitura: contaminado. |

Retrieval pode usar q01–q30: o embedding multilíngue foi escolhido por adequação ao
português, antes da comparação de desempenho nessas perguntas, não por busca da
melhor pontuação no conjunto. Declarar esse critério no relatório. Isso não torna
o benchmark independente: perguntas, relevâncias, filtros e limiar já foram vistos.
A ablação mede desempenho de desenvolvimento, não generalização fora da amostra.

Todo número de geração deve acompanhar conjunto/IDs, configuração, versões/hashes
de prompt e parser e o rótulo **limpo** ou **contaminado**, com motivo. Limpo refere-se
à ausência de ajuste prévio naquela configuração usando aquelas perguntas, não a
gold humano cego ou holdout de documentos. n11–n20 usam corpus conhecido e rótulos
de IA; sua rodada final não permite novas tentativas confirmatórias independentes.
Não mudar retrospectivamente o rótulo da execução original porque os resultados
foram lidos depois. Para nova avaliação limpa, congelar a configuração antes de
criar e executar um novo conjunto, sem ajustes intermediários e com origem dos
julgamentos registrada. Resultados legados sem proveniência suficiente devem ser
marcados contaminado, com a lacuna explicitada.

### Hipóteses e variáveis antes de executar

A ablação autorizada por este protocolo é de **modelo de embedding**:

- Referência: sentence-transformers/all-MiniLM-L6-v2 (inglês).
- Variante: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2.
- Hipótese direcional: a variante multilíngue supera a referência em recall
  limitado@5 sem filtros nas perguntas respondíveis em pt-BR. Essa é a medida
  primária pré-definida; os demais k, métricas e o modo filtrado são complementares.
- Hipótese nula operacional: a diferença média pareada da medida primária é zero;
  resultado negativo ou empate será publicado sem trocar a medida primária.

Manter corpus gold isolado, revisão human-v2, IDs/relevâncias, texto, chunking,
normalização L2, distância cosseno, filtros, desempate e procedimento de ranking
iguais. Usar coleções separadas, reconstruídas do mesmo corpus, e registrar revisão
dos modelos, hashes de dados/código e ambiente. A dimensão diferente dos vetores
é parte da troca de modelo. Não usar coleção histórica de outro corpus. Sem pesos
ou ambiente necessários, registrar não executado; não substituir silenciosamente.

Comparações com aleatório e lexical usam os baselines já definidos; seus resultados
já foram observados e não constituem hipótese prospectiva de superioridade. Caso
se decida testar contexto, chunking, busca híbrida, reranker ou geração, registrar
antes da execução uma hipótese específica, referência, única variável alterada e
medida primária. Não executar essas variantes por este registro. O pacote v3 mudou
vários eixos juntos e continua sem interpretação causal de ablação isolada.

### Métricas congeladas

Reutilizar exatamente as definições acima e evaluation/baselines.py: para pergunta
respondível, R são IDs relevantes congelados, L_k contém até k IDs distintos,
H = |R interseção L_k|; k = 1, 3, 5, 8.

- hit@k = 1 quando H > 0; senão 0.
- recall@k limitado = H / min(k, |R|).
- MRR@k por pergunta = 1 / posição do primeiro relevante até k, ou zero sem acerto;
  o agregado é a média desses valores.
- precision@k = H / k, inclusive quando há menos resultados que k.

Médias macro nas 24 respondíveis, sem remover erros ou perguntas difíceis. Recall
clássico H/|R|, se apresentado, terá nome próprio. O campo recall_at_k no avaliador
legado retrieval.py é clássico; não misturar esse campo com recall limitado.
As seis negativas ficam fora dessas quatro médias e têm abstenção/falsa aceitação
reportadas separadamente, com contagens e denominadores. Falha de execução não é
abstenção e deve impedir apresentar uma rodada incompleta como comparação completa.

Ranking principal sem corte por score, nos dois modos: sem filtro e com os mesmos
filtros estruturais. A comparação operacional usa o corte fixo 0.25 para embeddings,
score > 0 no lexical e nenhum limiar no aleatório, declarando que esses cortes não
são equivalentes. Não recalibrar min_score, selecionar k ou alterar relevâncias
com base nos novos valores. O candidato histórico 0.287 não será promovido.

### Unidade de comparação: pergunta, não apenas média

Parear estritamente por ID, conjunto/revisão, modo e k. Para cada métrica, salvar
valor da referência, valor da variante e delta = variante - referência. Vitória
se delta > 1e-12; derrota se delta < -1e-12; empate nos demais casos. A tolerância
serve só a ruído numérico, não a relevância prática. Reportar vitórias/empates/
derrotas e denominador, diferenças por pergunta e média dos deltas, além das médias
macro. Nenhuma pergunta ausente pode ser descartada silenciosamente; comparações
incompletas devem ser identificadas como tais. Não escolher a variante vencedora
apenas por uma média ou pela métrica que mais melhorou depois da execução.

O resumo primário é recall limitado@5 sem filtros; os demais resultados permanecem
visíveis, inclusive se mostrarem trade-offs. Vitória por hit@k pode ser empate em
outra métrica: contar separadamente, sem inventar placar único pós-resultado.
Para o aleatório, manter as 200 seeds 42..241 e a mesma permutação por pergunta/seed
entre k. A referência pareada de cada pergunta é a média dessa métrica nas 200
repetições; não tratar seeds como perguntas independentes. Preservar também a
dispersão entre repetições do agregado. Não alegar significância estatística a
partir da simples contagem de vitórias.

Publicar resultados contrários às hipóteses e limitações de exposição, tamanho
do conjunto, rótulos e ausência de revisão independente, sem reescrever este
protocolo para ajustá-lo aos resultados. Mudança futura exige nova entrada datada,
anterior à nova execução, preservando esta versão e os artefatos anteriores.


### Extensão prévia da matriz de retrieval CPU — 2026-11-06

Antes de executar esta nova rodada, incorporar o pedido de k=3,5,8,12. Manter
k=1 como referência adicional do protocolo anterior, sem substituir ou selecionar
a medida primária: recall limitado@5 sem filtros, multilíngue versus inglês.
Executar os dois MiniLM previstos; E5 é opcional e não integra esta rodada.

O fator filtro nesta ablação significa **somente restaurant_id** versus nenhum
filtro. Item e datas não são aplicados em nenhum dos dois modos, diferentemente
do benchmark histórico com filtros estruturais completos. Não comparar seus
números como se o escopo fosse igual. Não inserir labels de aspecto no filtro.

Reconstruir o mesmo corpus de 100 reviews de human-v2 em collections novas e
separadas por modelo, em banco temporário isolado, sem tocar o índice operacional.
Cada review permanece inteira; impedir truncamento de documentos e consultas
nos limites reais dos dois modelos. Se alguma exceder, interromper e registrar
uma decisão de chunking antes de medir, sem truncamento silencioso. Recuperar todos
os candidatos elegíveis, ordenar por cosseno e desempatar por ID, para remover a
aproximação/top-k de candidatos como fator nesta base pequena. Não medir latência
como benchmark de produção com esse procedimento exaustivo.

Relatar a matriz completa: dois embeddings, lexical e aleatório; dois modos;
k=1,3,5,8,12; ranking sem corte e operacional com cortes já definidos. Aleatório:
200 seeds 42..241, com média por pergunta para comparações e dispersão dos agregados.
Negativas continuam separadas das métricas de ranking das 24 respondíveis.

Salvar métricas e IDs por pergunta; placares pareados por métrica/k/modo para
multilíngue versus inglês e cada embedding versus lexical/aleatório. Comparar
com/sem restaurante por método e os incrementos entre k sucessivos. Exibir também
recall clássico, número de relevantes recuperados e irrelevantes adicionados,
pois recall limitado muda de denominador com k e não é monotônico. Não escolher
k automaticamente nem alterar defaults após ver a matriz. Reportar todas as
configurações, erros e modelos tentados; registrar revisões dos pesos, ambiente,
hashes de código/dados/protocolo e critérios já escolhidos por idioma. Esta rodada
é retrieval de desenvolvimento exposto; não contém avaliação nova de geração.


### Resultado da ablação CPU registrada

Rodada concluída sem alterar o protocolo: a hipótese direcional primária não foi
corroborada (recall limitado@5 sem filtros: delta multilíngue menos inglês
-0,006944; 4 vitórias, 16 empates, 4 derrotas nas 24 respondíveis).
A matriz completa, os incrementos de ruído por k e as comparações pareadas estão
em [análise CPU](../reports/retrieval-cpu-ablation-v1/ANALISE.md). Não promover
configurações nem limiares com base nesta avaliação de desenvolvimento exposta.


## Consolidação retrospectiva de geração sem novas variantes

Antes dos novos julgamentos, fixar a [rubrica v1](../reports/generation-retrospective-v1/RUBRICA.md):
sustentada/parcial/sem_suporte e, separadamente, responde à pergunta. Leitura de IA
com escopo explícito, revisão humana assistida somente após resposta de João.
Funil distingue contrato textual (sem schema JSON), schema, IDs, trechos e aceitação;
colunas têm denominadores próprios e não constituem uma sequência universal.
Não executar inferência, LLM-as-judge ou novas variantes; preservar todos os brutos.

Revisão humana assistida concluída nos dez casos de entrevista da retrospectiva:
3 sustentados, 2 parciais, 5 sem suporte; 2 sustentados e pertinentes. Concordância
assistida com IA: 10/10 nos dois eixos, sem caráter cego/independente e sem juiz LLM.
A seleção dirigida por falhas e distribuída entre versões não estima acurácia global.
Observações humanas, auxílio no enquadramento e confirmações estão preservados por caso.


## Consolidação de custo e latência sem novos benchmarks

Usar exclusivamente os artefatos medidos, com ambiente/commit ao lado dos valores.
Separar smoke, estatísticas da rodada, tempo de geração e carga repetida como atributo;
não somar a carga por pergunta nem duplicar a carga compartilhada de v3. D conta
somente as 25 tentativas corretivas novas, não tempos herdados de B como outra rodada.
GB e GiB, memória alocada e reservada são medidas distintas. Todas as rodadas GPU
registradas usam Kaggle/Tesla T4 e pesos NF4, mesmo com compute_dtype=float16.
Latências isoladas de embedding/retrieval em CPU não foram registradas; permanecem
pendentes. O total das ablações CPU inclui carga/cache/download e não é latência de
consulta. Comparação com pesos integrais FP16 em ambiente T4 16 GB fica pendente,
sem execução nesta etapa. Sem tarifa/duração de sessão, não calcular custo monetário.
[Valores, ambientes e fontes](../reports/cost-latency-consolidation-v1/README.md).


## Reserva de perguntas para avaliação final sem novos ajustes

Reservar dez perguntas novas (n21–n30), com sete respondíveis e três negativas,
antes de qualquer resultado delas. V3, configuração e corpus preservados por hashes;
nenhum retrieval ou LLM executado. Uma única rodada futura, no máximo uma chamada
por pergunta, sem retry corretivo nem ajuste posterior; indeterminadas não são
repetidas automaticamente. O conjunto não entra em calibração, treino ou demos.
Fechamento procedural, não criptografia; autoria/labels de IA em corpus conhecido
não constituem holdout de documentos ou gold humano independente. A geração limpa
já medida permanece em nove chamadas. Runner de entrada/ledger e revisão dos pesos
devem ser preparados antes da abertura, sem mudar o comportamento congelado.
[Protocolo e pendências](reserved-evaluation.md). Se não houver execução, manter
a amostra pequena como limitação e este conjunto como trabalho futuro.


## Momento das medições ainda pendentes

Latências isoladas de embedding de consulta e retrieval em CPU serão medidas uma
única vez na integração da API, com protocolo/repetições fixados antes e hardware
identificado. Comparação NF4 versus pesos integrais FP16 em T4 16 GB fica para o
benchmark dedicado, sem execução agora e sem presumir que caberá na memória.
As perguntas reservadas não entram nessas medições exploratórias.
[Plano e separação dos tempos](future-measurements.md). README reduzido a cinco
manchetes geradas; instalação e histórico preservados em project-guide.md.


## Contrato da API e seleção de backends — decisão anterior à implementação

Status: especificação prospectiva api-v1. api.py ainda está vazio; backends, DTOs,
rotas e tempos por etapa descritos abaixo NÃO estão implementados. Nenhuma inferência
ou medição será feita nesta etapa. Preservar o núcleo/prompt/parser v3 congelados e
os contratos legados da CLI; implementar a fachada da API em adaptadores próprios.

### Três backends explícitos, sem fallback silencioso

LLM_BACKEND é configuração do servidor, obrigatória para a API, com valores real,
fake ou replay. O cliente não escolhe o backend no corpo da pergunta. Valor inválido
é erro de configuração antes de atender requisições. Indisponibilidade de dependência
com configuração válida é comunicada como 503 quando necessária ao atendimento.

| Backend | Comportamento | Identificação obrigatória na resposta e interface |
| --- | --- | --- |
| real | Mistral-7B-Instruct-v0.2 em GPU, NF4 4-bits, uma instância lazy por processo; sem GPU/modelo acessível, falha explícita. | backend=real; is_replay=false; is_simulation=false; rótulo Inferência ao vivo. |
| fake | JSON v3 fixo de fixture configurada; sem baixar/carregar LLM. Pode simular recusa; respostas com fontes exigem fixtures compatíveis com o contexto de teste e a mesma validação. | backend=fake; is_simulation=true; rótulo SIMULAÇÃO — resposta fixa de teste. |
| replay | Resposta gravada de uma pergunta conhecida, com contexto arquivado e identidade verificável; sem LLM ou retrieval ao vivo. | backend=replay; is_replay=true; rótulo REPLAY — resposta gravada no Kaggle; não gerada agora. |

A interface mantém o rótulo visível junto da resposta, não apenas em tooltip ou log.
Replays mostram a origem da rodada e identificam tempos históricos separadamente.
Nunca apresentar spinner/texto de geração ao vivo em replay ou fake. Não mudar de
real para fake/replay ao falhar. Backend/configuração são imutáveis por instância;
testes podem injetar doubles explicitamente. Importar/iniciar fake ou replay não
pode carregar Transformers/bitsandbytes nem verificar GPU como pré-condição.

A API seleciona explicitamente prompt partner-copilot-v3, parser-v3, context_k=8,
max_new_tokens=512, temperatura=0 e seed=42, com min_score=0.25. Configuração explícita
incompatível com esse perfil é rejeitada, sem substituição silenciosa. Não mudar
os defaults legados globais de v1 da CLI para cumprir esse perfil da API.

### Entrada: POST /v1/ask

Objeto JSON estrito, extra=forbid em todos os níveis. Não aceitar coerção de bool ou
strings para k. Remover apenas whitespace externo de strings; não alterar caixa,
acentos ou espaços internos da pergunta. Validar antes de acessar backend/índice.

| Campo | Regra |
| --- | --- |
| restaurant_id | Obrigatório, str de 1 a 64 caracteres após strip; padrão [A-Za-z0-9][A-Za-z0-9_-]{0,63}. Sempre restringe a busca; nunca inferir do texto da pergunta. |
| question | Obrigatório, str não vazia após strip, no máximo 2.000 caracteres Unicode; o orçamento real de tokens continua obrigatório antes de chamar o modelo. |
| filters | Objeto opcional; omitido ou null equivale a ausência de filtros adicionais; campos extras rejeitados. |
| filters.start_date / end_date | Datas ISO YYYY-MM-DD opcionais, limites inclusivos; aceitar uma ponta aberta, rejeitar início maior que fim. Chroma usa created_at_int, nunca comparação numérica sobre texto ISO. |
| filters.aspect | Opcional: sabor, tempo_entrega, temperatura, embalagem, preco ou atendimento. Mantém o contrato atual: filtra aspect_<nome>=neg, isto é, reclamações desse aspecto, não qualquer menção. |
| filters.item | Str opcional, 1 a 200 caracteres após strip, igualdade exata; vazio é inválido. |
| k | Int opcional, default 8, mínimo 1 e teto público 12; fora do intervalo é 422, nunca clamp silencioso. |

Campos opcionais null equivalem a ausentes, sem criar filtros vazios. Não expor where
arbitrário do Chroma, limiar, backend ou versões do prompt no request. Categoria,
cidade/bairro e polaridade positiva não entram neste primeiro DTO; não aceitar
campos ignorados silenciosamente. A interface deve chamar o filtro aspect de
reclamações do aspecto, para não prometer a seleção de elogios.

k controla o limite do retrieval; até 2*k candidatos antes do corte fixo por score.
O contexto contém até min(k, 8, documentos retornados), sem relaxar filtro/limiar.
Documentos/chunks e IDs distintos de reviews continuam unidades separadas. Não
mutar um Retriever compartilhado por requisição para trocar k; usar configuração
local ao request com store/embedder reutilizados. Teto 12 é da API, embora o núcleo
legado admita até 50. Essas opções não alteram os números de avaliação já publicados.

### Replay: catálogo explícito e contexto de origem preservado

Replay é reprodução de um resultado inteiro de avaliação, não um LLM falso ligado
a uma nova busca. Isso evita reutilizar uma citação do corpus gold em um contexto
diferente do índice RAG operacional. Usar exclusivamente o contexto arquivado,
com os hashes do corpus/arquivo, versões de prompt/parser e configuração da rodada.
Não inserir gold no índice de produção nem declarar que consultou dados atuais.

O catálogo é uma allowlist aprovada: saída real de Kaggle, aceita pelo parser v3,
IDs/trechos válidos no contexto arquivado e conteúdo sustentado/pertinente aprovado
explicitamente pelo responsável, com origem e método da revisão registrados.
Aceitação de schema sozinha não aprova replay; n12 e a q23 irrelevante não entram.
Não converter texto legado v2 em JSON v3 alegando que foi essa a saída do modelo.
Não corrigir n14 para fazê-la parecer aceita na rodada original.

Pendência concreta: na seleção humana assistida atual, os dois casos sustentados
e pertinentes são n14-v3 (rejeitada pelo parser) e q05-C (contrato textual v2).
Nenhum satisfaz simultaneamente a política de replay v3. Portanto o catálogo não
está pronto; requer curadoria/aprovação de outros registros v3 já existentes, sem
novas inferências. Não inventar essa aprovação para desbloquear a demo. Catálogo
vazio/ilegível é replay_unavailable (503), não uma resposta fictícia de sucesso.

Chave de seleção: JSON canônico de restaurant_id, question após strip externo,
filtros normalizados (null/ausente equivalentes; datas ISO), k efetivo, versões e
configuração efetiva registrada. Preservar caixa/acentos/espaços internos; não usar
similaridade semântica, substring ou fuzzy match para escolher uma gravação.
Mudança de pergunta, restaurante, período, aspecto, item ou k exige outra entrada.
Sem correspondência: replay_not_found (404), sem gerar resposta nem fingir abstenção
por falta de evidência. A demo pode oferecer apenas perguntas aprovadas do catálogo.

Revalidar entrada, integridade e saída arquivada no contexto correspondente antes
de servir. Manter o JSON original e seu bruto/sufixo no artefato; a resposta pública
expõe apenas a parte validada. Se o arquivo válido mudou de snapshot/versão em relação
ao catálogo, retornar replay_snapshot_mismatch (409). Não trocar a evidência ou
abrir exceção ao parser. Não incluir perguntas do conjunto reservado em catálogo,
fixtures, exemplos de interface ou testes de desenvolvimento.

### Saída de sucesso: envelope api-v1 com objeto v3 preservado

HTTP 200 somente para resposta validada ou abstenção válida. DTO público versionado
separado do Answer legado: hoje a pipeline descarta as afirmações/trechos ao renderizar
o texto, e seu llm_called também é usado para doubles. A fachada deverá preservar o
objeto v3 e distinguir chamada do backend de inferência real, sem alterar o parser
congelado nem falsificar os invariantes do modelo legado.

| Campo | Conteúdo e invariantes |
| --- | --- |
| schema_version | api-v1; distinto da versão do prompt e da versão interna do journal. |
| result | Objeto v3: abstem: bool e afirmacoes: lista de {texto, fontes: [{review_id, trecho}]}; tipos estritos e sem campos extras. |
| answer | Texto renderizado por código a partir das afirmações e IDs validados; em abstenção, a frase pública fixa já definida. |
| sources | IDs de reviews citadas, únicos e na ordem da primeira citação; não a lista completa do retrieval. |
| abstained | Igual a result.abstem, que é true se e somente se afirmacoes está vazia. |
| abstention_reason | null em resposta normal; retriever_empty ou llm_insufficient_evidence em abstenção, preservando a origem histórica em replay. |
| metadata.request_id | Identificador opaco gerado pelo serviço para correlacionar resposta e logs. |
| metadata.backend / is_replay / is_simulation / mode_label | Origem atual e rótulo fixo, sempre presentes, inclusive nas abstenções. |
| metadata.prompt_version / parser_version | Versões configuradas/validadas; replay usa as versões efetivas do registro aprovado. |
| metadata.backend_called / llm_called | Backend atual foi invocado versus inferência Mistral real nesta requisição; fake/replay têm llm_called=false. |
| metadata.retrieved_documents / context_documents | Contagens de documentos/chunks; em replay são históricas e metadata.context_origin=recorded_eval_snapshot; nos demais, current_request. |
| metadata.timings_ms | Tempos atuais por etapa, definidos abaixo; nunca preencher com valores históricos de Kaggle. |
| metadata.source_run | null em real/fake; em replay, experimento/question_id de origem, corpus isolado, commit, hashes, método de aprovação e ambiente/hardware de origem. Datas ausentes no arquivo permanecem null, sem usar mtime como se fosse data da execução. |
| metadata.source_run.historical_metrics | Métricas originais, com hardware/tempo/unidades, em bloco separado; não entram em timings_ms da requisição atual. |

Resposta normal exige pelo menos uma afirmação com fontes. Todos os IDs precisam
estar no contexto efetivamente usado e todos os trechos nele contidos literalmente;
qualquer fonte inválida rejeita a resposta inteira. Não remover uma citação para
publicar o restante. Ter fonte/trecho não prova sustentação semântica; manter esse
limite também na interface e nos relatórios. Excertos são dados, não HTML confiável.

No caminho real/fake com retrieval vazio: result={abstem:true, afirmacoes:[]},
answer=Não há evidência suficiente nas avaliações fornecidas., sources=[],
abstained=true, abstention_reason=retriever_empty, contagens zero e nenhuma chamada
do backend/LLM. Em real com recusa válida pelo modelo, manter contagens reais,
llm_called=true e llm_insufficient_evidence. Fake identifica simulação; replay
preserva o motivo da gravação, mas nunca atribui inferência à requisição atual.

### Tempos: medir etapas atuais, sem transplantar latência da T4

Todos em milissegundos, finitos e não negativos, com perf_counter. total_ms começa
após a validação da entrada na aplicação e termina após validar/montar a saída;
não inclui transporte HTTP. A soma das etapas não precisa ser igual ao total:
existe orquestração fora dos intervalos. Não estimar uma etapa por subtração.

| Campo em metadata.timings_ms | Intervalo |
| --- | --- |
| embedding_search_ms | Chamada completa do retriever: embedding de consulta, busca vetorial, filtros/corte e conversão dos documentos; inclui carga lazy de embedding, se ocorrer. |
| generation_ms | Etapa de preparação do prompt, obtenção/carga lazy do backend, espera e chamada até a saída bruta/decode; exclui validação de conteúdo/contrato. Em fake mede só o caminho simulado, rotulado como tal. |
| validation_ms | Decode/schema v3, IDs, trechos, consistência e construção/validação do DTO público; não certifica entailment. |
| replay_lookup_ms | Somente em replay: seleção da gravação/artefato; separado de geração. |
| total_ms | Tempo da operação na aplicação, no hardware atual, com as exclusões acima. |

Em abstenção real/fake por contexto vazio, generation_ms=0 (etapa pulada). Em replay,
embedding_search_ms e generation_ms são null (não executados), replay_lookup_ms,
validation_ms e total_ms são medidos de verdade. Zero não é benchmark de modelo
instantâneo e null não é métrica faltante a ser preenchida com o tempo antigo.
Se for exposto model_load_ms, medir apenas a carga ocorrida nesta requisição, como
subconjunto de generation_ms, não somá-la novamente. generation_metrics do provider
(exclui carga/espera pelo lock) é outra medida e deve ser nomeada separadamente.

O backend fake permite testes sem GPU com relógio/doubles; não valida desempenho.
A medição isolada de embedding e busca em CPU será feita uma vez na integração da
API, conforme future-measurements.md; a dupla embedding+busca é o contrato público,
mas a instrumentação deve permitir separar os dois no benchmark definido previamente.
Nenhuma nova medição ou comparação FP16 é autorizada por esta decisão documental.

### Erros: códigos estáveis e nenhuma saída bruta como resposta válida

Envelope único de erro: {error: {code, message, details}, request_id, backend}.
Os códigos/mensagens/detalhes são próprios de cada situação; nunca devolver Answer
ou result junto de um erro. A interface exibe erro e request_id, não tenta renderizar
raw_response de um HTTP não-200. Modelos rejeitados não viram abstenção silenciosa.

| Situação | HTTP | error.code | Corpo público / comportamento |
| --- | --- | --- | --- |
| JSON malformado, campo ausente/extra, tamanho, tipo, enum, datas ou k inválidos | 422 | invalid_request | Mensagem de entrada inválida e lista de campos/regras/limites; sem ecoar o conteúdo recebido. Nenhum retrieval/backend iniciado. |
| Nenhum documento satisfaz restaurante/filtros/limiar | 200 | Não é erro | Envelope de abstenção retriever_empty acima; sem LLM. Restaurante válido sem reviews segue esse caminho, sem fallback para outro restaurante. |
| Schema do modelo, ID, trecho ou consistência rejeitados | 502 | generation_contract_failed | Mensagem Não foi possível validar uma resposta; details.reason=invalid_schema, invalid_source_id ou quote_mismatch; contagens opcionais, sem resposta bruta ou citações inválidas. Sem retry automático. |
| Modelo/GPU inacessível, download/load/OOM ou backend necessário indisponível | 503 | model_unavailable | Mensagem de indisponibilidade temporária/configurada; sem fingir resposta ou trocar backend. Detalhes técnicos ficam fora do corpo público. |
| Replay sem entrada para a chave exata | 404 | replay_not_found | Informar que a pergunta/configuração não está disponível na demonstração gravada; não declarar ausência de evidência nos dados. |
| Catálogo de replay vazio, ilegível ou sem aprovação | 503 | replay_unavailable | Informar que o catálogo de demonstração não está pronto, sem gerar resposta substituta. |
| Gravação diverge do snapshot/versões configurados | 409 | replay_snapshot_mismatch | Informar incompatibilidade da gravação e configuração; não revalidar contra um contexto diferente. |
| Índice/embedder obrigatório indisponível | 503 | retrieval_unavailable | Informar indisponibilidade da consulta; não confundir falha de infraestrutura com lista vazia. |
| Tempo limite configurado excedido | 504 | backend_timeout | Informar interrupção por tempo, sem resposta parcial e sem nova chamada automática. |
| Exceção inesperada de programação | 500 | internal_error | Envelope padronizado e request_id, sem stack trace; só este fallback usa 500, nunca os cenários conhecidos acima. |

Em 502, a geração pode ter ocorrido, mas seu texto não será mostrado como resposta,
parcial ou alternativa. O cliente só vê o motivo estável e o identificador de suporte.
O bruto pode permanecer no journal de avaliação/diagnóstico controlado, ligado ao
request_id, nunca em logs normais/UI por padrão. Não expor token, prompt, contexto,
caminho local, stack trace ou mensagens internas das bibliotecas no corpo do erro.
Validação do request deve converter os erros do framework para esse envelope,
sem repassar input/context de ValidationError indiscriminadamente.

Retry-After só será enviado se houver estimativa real de recuperação; 502 não
sugere retry corretivo. Em erros, metadados parciais de tempo podem ser registrados
internamente; não inventar valores para etapas não concluídas. Os códigos conhecidos
não dependem de procurar frases em str(exception): usar exceções/tipos próprios.

### Critérios de aceite para a implementação posterior

Verificar com testes sem GPU: limites/filtros/k; todos os backends rotulados; real
indisponível sem fallback; vazio não chama backend; estrutura v3 preservada; rejeição
não vaza bruto; IDs/trechos inválidos rejeitam tudo; replay exato sem inferência/
embedding e sem gold no índice operacional; chave divergente é 404; snapshot divergente
é 409; indisponibilidade é 503; métricas históricas não se passam por latência atual.
Incluir casos de conteúdo incorreto que passam a estrutura para não prometer que o
parser resolve fidelidade. Curadoria do catálogo continua uma pendência anterior
à demo; nenhuma aprovação humana nova foi produzida por esta especificação.


## Implementação da API: startup, concorrência e logs

A inicialização da API tentará carregar índice, embedder e backend uma única vez
por processo. Isso substitui a carga lazy por requisição descrita anteriormente
para a fachada HTTP; a CLI e o núcleo congelado permanecem intactos. Falhas de
componentes degradam /health (503), sem impedir o serviço de subir, e são expostas
por códigos estáveis, não mensagens de exceção. Endpoints /health, /ask e menus de
restaurantes/itens, com aliases /v1, usam os DTOs já decididos.
Geração usa um semáforo único por processo; servir um único worker por GPU.
Timeout total padrão 60 s, configurável, e máximo de oito requests pendentes;
fila cheia retorna 429 resource_busy. Timeout não cancela CUDA/threads: o semáforo
fica ocupado até a chamada terminar e a saída atrasada é descartada. Requisições
expiradas na fila não iniciam inferência. Nenhum retry automático.
Logs estruturados contêm request_id gerado pelo serviço, restaurant_id, backend,
versão do prompt, latências e código/tipo de erro. Não registrar question, resposta,
reviews, prompts, segredos ou stack trace por hábito. Dados reais exigem análise
de anonimização/retenção e controles adequados à LGPD; não afirmar conformidade
legal automática. Artefatos brutos de avaliação não viram logs padrão da API.
Antes da medição CPU, fixar oito consultas operacionais inventadas (uma por
restaurante), uma passagem de warm-up e cinco repetições, total 40 amostras.
Modelo/índice carregados antes do timer; medir embedding e busca separadamente
por relógio monotônico, sem subtração. Corpus somente split RAG registrado;
nenhum gold/reservado. Registrar hardware, RAM, threads, versões e hashes.
Não repetir a rodada para escolher resultado; na ausência de índice válido,
registrar indisponibilidade e não publicar latência baseada em doubles.

API implementada em fachada nova, sem alterar o núcleo congelado. Tempos isolados
embedding_ms/search_ms são intervalos diretos, além da etapa combinada. A coleta
CPU foi concluída uma única vez, 40 amostras e 862 reviews RAG; fontes, hardware,
versões e limitações em reports/api-cpu-latency-v1/. Falha de pré-flight ocorreu
antes de carga/amostras; nenhuma medição foi descartada. Catálogo replay continua
vazio até curadoria explícita; não houve aprovação humana ou inferência nova.
[Uso, erros e concorrência](api.md).

Esclarecimento de dependências: fake não carrega o LLM/quantização, mas usa
Transformers/PyTorch em CPU para o embedder quando ligado a um índice real.
Replay usa só o catálogo/contexto arquivado e não importa runtimes de modelos.
Isso esclarece a restrição anterior sobre carga de Transformers, que não exclui
o encoder de embeddings CPU necessário ao caminho fake com busca real.


### CI CPU e isolamento dos testes HTTP

A matriz remota usa Python 3.12 e 3.13; 3.13 acompanha Kaggle, 3.12 cobre servidor.
O mínimo 3.10 declarado no pacote não implica cobertura de todas as versões.
Instalar apenas requirements-ci.txt, com cache pip e Ruff 0.17.3; executar lint,
formatação, seleção explícita de testes CPU com exclusão gpu e reprodução dos
resultados. Não instalar os extras completos nem baixar modelos no CI.
Um subprocesso bloqueia imports pesados e executa a importação da API e todos os
testes HTTP fake/replay; isso verifica o isolamento mesmo no PC com torch instalado.
A suíte completa com Chroma é uma verificação local distinta. Badge aponta para o
workflow real; sucesso só deve ser declarado após a execução remota terminar.


### Empacotamento CPU e bootstrap persistente

Imagem CPU com Python 3.13 e torch da distribuição CPU, sem dependências de
quantização. Backend permitido fake ou replay. Usuário UID/GID 10001; HEALTHCHECK
consulta saúde real; configuração por ambiente; contexto Docker por allowlist.
Nenhum `.env`, peso, cache, Chroma ou relatório de experimento entra na imagem.
Fake reconstrói somente o RAG versionado no primeiro uso do volume, com lock,
upserts idempotentes, validação completa e marcador atômico. Mudança de identidade
exige novo volume, sem apagar o anterior. Replay não precisa de índice, pois usa
contexto arquivado validado; catálogo aprovado é montado externamente, sem falsear
aprovações. Bootstrap libera seu encoder antes de iniciar o processo da API.
Docker está ausente no PC: testes unitários não atestam build/execução da imagem.
A orientação CUDA/--gpus é explicitamente não testada, sem alegação de suporte
verificado. Faixas de dependências e revisão de encoder não fixada limitam a
reprodução bit a bit; dados/splits permanecem checados por hash.


### Demo local com contexto integral e exemplos honestos

Cliente Gradio 6, em processo separado da API, sem carga de modelos na interface.
Cada afirmação mostra as fontes completas em paralelo, além da saída estruturada,
abstenção e versão do prompt. A API adiciona source_reviews; com chunks, obtém
originais do RAG validado carregados uma vez. Não rotular chunk como fonte inteira;
verificar também a presença literal do trecho no original e o restaurante da fonte.
Dados sintéticos, fake e replay são explicitamente rotulados. Replay preserva
contexto arquivado, não busca ao vivo. A área histórica mostra n17, n20 e n12,
com hashes, saída original, limites de revisão e indicação de gravação. Não é um
atalho para o catálogo de replay aprovado, que continua pendente. Exemplos são
regenerados sem inferência; nenhum conjunto reservado é aberto. Sem Space nesta
entrega; publicação, link temporário GPU e tag não são executados automaticamente.


### Fechamento da versão MVP

README com execução CPU em três comandos, testes, cinco linhas de arquitetura,
resultados e limites. O launcher local monta API e Gradio no mesmo serviço, mas
mantém a chamada HTTP à API e prepara o índice em subprocesso para liberar o
encoder do bootstrap. Não carrega Mistral no modo fake. Configuração de ambiente
ou .env prevalece sobre defaults locais; real é recusado nesse launcher CPU.
Notas v0.1-rag-mvp declaram n12/n15/n16, QLoRA, FP16/T4, Space e Docker não testado.
Documento de status do estudo criado a pedido de João por não existir no repositório.
Commit enviado deve passar no CI remoto antes de criar/enviar tag anotada; verificar
que o SHA da execução bem-sucedida é exatamente o SHA da tag, sem mover tag existente.


### ABSA: tarefa, rótulos de treino e ambiguidade

A entrada é o texto de uma review. A saída é um objeto JSON com o mapa `aspects`.
As chaves permitidas são `sabor`, `tempo_entrega`, `temperatura`, `embalagem`,
`preco` e `atendimento`. Cada aspecto com opinião identificável recebe `pos` ou
`neg`. Omitir aspectos sem evidência de polaridade. Quando a review inteira não
contém opinião identificável, retornar `{"aspects": {}}`. Para elogio e crítica
explícitos ao mesmo aspecto, aplicar a regra `neg` do guia congelado.

O treino supervisionado parte dos rótulos sintéticos do gerador no `train_pool`
versionado. O texto foi construído a partir desses rótulos, que oferecem supervisão
consistente sem custo de inferência. O Mistral como professor adicionaria custo de
GPU e ruído de anotação. A correspondência entre rótulo e template ajuda no treino,
mas uma avaliação com os mesmos padrões pode inflar o F1 por memorização. A defesa
é a separação do gold e o protocolo de avaliação independente, com controle de
sobreposição de templates. O gold, suas duplicatas em quarentena e o conjunto
reservado de geração ficam fora do treino. Se houver tempo, o Mistral pode
parafrasear uma pequena fração do treino. A variante só entra depois de uma
checagem manual por amostra da preservação dos aspectos e polaridades.

Reviews com ambiguidade sinalizada na preparação ficam fora do treino nesta
primeira versão. Guardar o ID e o motivo em metadados de auditoria, fora do JSON
alvo. Pelo guia congelado, “o gosto estava diferente do habitual” sem julgamento
explícito é ambíguo e deixa `sabor` ausente. Crítica ou estranheza explícita recebe
`neg`. A decisão de relevância de q22 pertence à avaliação de retrieval e não
serve como rótulo de polaridade ABSA.

Na avaliação, marcar as reviews ambíguas pela leitura do texto e pelas notas do
guia antes de olhar as previsões. Usar o gold congelado como referência e calcular
F1 sobre pares exatos `(aspecto, polaridade)` em duas vistas da mesma execução:
o gold completo e o gold sem as reviews marcadas como ambíguas. Reportar ambas
as contagens de reviews e o número excluído. Esse recorte mede sensibilidade à
ambiguidade com o mesmo modelo e as mesmas previsões.
### ABSA: validação e reserva de templates

O manifesto fixa 1.263 reviews de treino, 140 de validação e 346 de teste
sintético reservado. Remover duplicatas de review inteira e excluir as famílias
ambíguas sinalizadas. Reservar 12 famílias aproximadas por frase normalizada,
item e minutos mascarados, com um template por par aspecto/polaridade. Reviews
que contêm essas famílias ficam fora de treino e validação. Escolher checkpoint
na validação e usar o gold congelado uma vez na avaliação final. Reportar F1 com
suporte por estrato de exposição e por ambiguidade.

A auditoria cega ao rótulo encontrou 207/294 ocorrências de frases do gold no
novo treino. O gold tem 100 reviews anotadas por IA e aguarda revisão humana
independente. [Protocolo e contagens](absa-splits.md).


### ABSA: referência humana congelada

A avaliação final usa as 100 anotações da versão `absa-human-v1`. O autor confirmou
13 omissões propostas na adjudicação assistida. Quatro reviews compõem o recorte
pré-definido de ambiguidade: duas de sabor diferente sem avaliação e duas de duração
sem julgamento. As nove omissões por elogio geral aplicam a regra de ausência de
aspecto específico. O manifesto humano registra os hashes, a exposição prévia e as
omissões por ID. A alocação de treino, validação e teste de templates segue o
manifesto de splits já auditado.


### ABSA: dataset conversacional e base QLoRA

Usar Qwen2.5-1.5B-Instruct na revisão `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`.
Exportar instrução e review em `user` e JSON canônico em `assistant`. Renderizar
com o template oficial do tokenizer fixado. A primeira rodada usa 1.263 exemplos
válidos sob o teto de 1.500 e 140 de validação. O máximo medido foi 219 tokens.
Adotar 256 como limite inicial da sequência. [Distribuição e perfil](absa-dataset.md).


### ABSA: protocolo de avaliação pré-treino

**Unidade e métricas.** Cada review contribui um conjunto de pares exatos
`(aspecto, polaridade)`. Para cada uma das 12 classes, contar TP, FP e FN por
correspondência na mesma review. Trocar a polaridade gera FP para a prevista e
FN para a esperada. Reportar precisão, recall, F1 e suporte de cada par, além
dos agregados por aspecto (somando as duas polaridades) e por polaridade
(somando os seis aspectos). O resultado principal é a média aritmética do F1
dos pares com suporte positivo no recorte. Informar quantos pares entram nessa
média e marcar classes sem suporte. Para classes com suporte, a precisão vale
zero quando não há predições, assim como o F1 quando precisão e recall somam
zero. Para os agregados sem denominador, reportar a métrica como indisponível.

**Validade.** Exigir um único objeto JSON completo com somente `aspects` na raiz,
mapa com os seis nomes permitidos, valores `pos` ou `neg` e chaves únicas.
Um mapa vazio é válido. Espaçamento e ordem de chaves não alteram a validade.
Resposta inválida produz zero pares previstos e perde todos os pares esperados
na review. Ela continua no denominador da taxa de validade, reportada como
contagem de saídas válidas sobre todas as reviews. Aplicar a mesma validação a
todos os métodos, sem reparo da saída ou segunda tentativa.

**Conjuntos e escolha do modelo.** Usar as 140 reviews de validação para
acompanhamento, hiperparâmetros e escolha de checkpoint. O gold humano congelado
com 100 reviews entra em uma única passada final por método, após fixar
checkpoint, exemplos few-shot, regras, configurações e parser. Reutilizar as
previsões para o gold completo, o recorte sem os quatro IDs ambíguos e as fatias
de famílias vistas, mistas e inéditas. Avaliar também as 346 reviews sintéticas
de templates reservados, com resultados separados para as 36 só com famílias
inéditas e as 310 mistas. Reportar contagens e suporte em cada recorte. O gold
tem apenas duas reviews exclusivamente inéditas, com leitura descritiva desse
resultado. A escolha de hiperparâmetros e de checkpoint termina antes de
consultar previsões ou métricas do gold e dos templates reservados.

**Baselines da avaliação final.** Medir Qwen2.5-1.5B-Instruct na mesma revisão do
modelo ajustado, em few-shot sem ajuste de pesos. Selecionar demonstrações
exclusivamente do treino e fixar a configuração de decodificação antes da
avaliação. Medir também regras simples por palavras-chave, definidas pelo guia
e pelo treino, com ajustes restritos à validação. Incluir o baseline clássico
de baixo custo com TF-IDF e regressão logística por aspecto, com classes
`ausente`, `pos` e `neg`, caso a implementação caiba antes da rodada final. Ajustar
vocabulário e pesos no treino e escolher parâmetros na validação. Omitir a
classe `ausente` da saída. Comparar todos os métodos nos mesmos IDs e reportar
quando o clássico superar QLoRA.

**Hipótese registrada.** QLoRA supera o few-shot em macro-F1 no gold completo.
Seu macro-F1 tende a ser menor em reviews com famílias inéditas que nas reviews
do gold com famílias vistas. Tratar a comparação por exposição como descritiva,
com suporte por classe e por grupo. Reportar os resultados que contrariem a
hipótese com as mesmas métricas e os mesmos recortes.


### ABSA: configuração do primeiro treino completo

Usar [absa-qlora-v1.json](../configs/absa-qlora-v1.json) com os hashes do
manifesto, a revisão Qwen e as versões validadas no smoke da T4. A primeira
execução usa até três épocas, seed 2718, LoRA r=8 e alpha=16 em `all-linear`,
NF4 com dupla quantização e compute FP16. Manter os adapters treináveis em FP32
após inicializar o TRL. O batch efetivo é cinco, com microbatch um e acumulação
cinco, sequência máxima de 256 tokens e perda restrita à completion. Preservar
AdamW e LR constante de 2e-4 do smoke para reduzir mudanças entre as execuções.
Conferir versões, hashes, ausência de truncamento e máscara antes do treino.

Medir `eval_loss` nas 140 reviews de validação ao fim de cada época e escolher
exclusivamente o menor valor finito. Em empate, preservar o primeiro checkpoint.
Salvar o adapter escolhido com seu hash, época e histórico de treino e validação.
A projeção é de 253 passos por época e cerca de 36,9 minutos para três épocas,
com base na mediana do smoke. O limite proposto para a sessão completa é de
60 minutos, incluindo carga, avaliação de validação e gravação dos checkpoints.

A auditoria da validação encontrou 317 de 377 ocorrências de frases (84,1%) e
213 de 272 frases distintas (78,3%) no treino, pela mesma normalização usada
no gold. A curva de validação serve à escolha de checkpoint dentro do corpus.
O teste de templates reservados mede desempenho fora das famílias vistas.
Após congelar o checkpoint, executar uma única passada por método em cada teste.
Reportar a diferença de F1 entre gold e templates reservados como achado, com
contagens e origem dos rótulos. As duas avaliações têm referências diferentes,
então a diferença bruta de F1 não isola o efeito dos templates.


### ABSA: portão de validade para a avaliação final

O `checkpoint-253` foi o melhor dos três checkpoints salvos ao fim das
épocas. O mínimo de perda entre avaliações é desconhecido. O cálculo é
teacher-forced sobre os tokens da resposta esperada, muitos deles parte da
estrutura determinística do JSON. A sobreposição de ocorrências de frases com
o treino é 84,1% na validação e 70,4% no gold. Esses fatores limitam a
interpretação da perda como evidência de generalização ou de desempenho em
geração livre.

Verificar o adapter pelo [manifesto de avaliação](../configs/absa-eval-v1.json).
Fixar decodificação gulosa, template oficial congelado e limite de 96 novos
tokens. Aplicar o contrato estrito pré-treino, com chaves únicas, sem reparo
ou tentativa adicional. Rodar as 140 reviews de validação primeiro. O portão
passa com até 7 saídas inválidas (5%). Acima disso, encerrar a sessão de
avaliação e investigar na validação. Uma execução incompleta também bloqueia
o acesso ao gold e ao teste reservado. A tolerância operacional de 5% foi
definida antes da geração. O F1 de validação é apenas diagnóstico.

Congelar antes da execução todos os comparadores. Few-shot usa quatro
demonstrações do treino, escolhidas deterministicamente pela cobertura de pares
ainda sem exemplo, com desempate por número de pares e ID. Regras usam
vocabulário fixo por aspecto e polaridade. O TF-IDF usa palavras e bigramas com
regressão logística balanceada por aspecto (classes ausente, pos e neg),
ajustada apenas no treino. O placar pareado usa F1 dos pares exatos por
review. Saída inválida recebe zero. Dois mapas vazios válidos recebem um.

## Enriquecimento ABSA na ingestão — desenho e protocolo exploratório

Executar o extrator em lotes sobre o texto integral, antes do chunking. Gerar
um resultado por review e versão do extrator, reaproveitando-o nas reingestões
enquanto o texto e a versão forem os mesmos. Replicar o resultado em todos os
chunks da review. A consulta usa apenas os metadados já indexados, sem chamar
o extrator.

Gravar `aspect_<nome>=pos|neg` e manter `aspects_json` sincronizado. Aspectos
ausentes ficam sem chave. Usar `absa_extractor_version` como identificador
escalar da versão, resolvido em manifesto para as revisões imutáveis do modelo
base e do adapter e para as versões do prompt e do parser. Gravar também
`absa_status=ok|error`: um mapa vazio válido é `ok` e uma tentativa que falhou é
`error`. Reviews legadas sem versão, com versão antiga, com erro ou com texto
alterado ficam elegíveis para reprocessamento.

Se o JSON for inválido ou violar o schema, indexar normalmente o texto, o
embedding e os metadados básicos. Gravar mapa vazio e remover chaves de aspectos
antigas, inclusive dos chunks reaproveitados. Registrar ID, versão e código do
erro em log, sem texto da review nem saída bruta. Em coleções enriquecidas,
as previsões substituem os rótulos sintéticos no índice. Os arquivos de origem
e as referências de relevância ficam congelados.

### Hipótese e perguntas elegíveis

Em perguntas sobre reclamações de um aspecto, aplicar
`aspect_<nome>=neg` aumenta a precisão da busca. Erros de omissão ou de
polaridade do extrator podem excluir reviews relevantes. Fixar o mapeamento
pelo texto das perguntas, incluindo paráfrases, antes de gerar predições:

| Aspecto | Perguntas respondíveis |
| --- | --- |
| embalagem | q01, q05, q21 |
| atendimento | q02, q23 |
| temperatura | q03, q06, q19 |
| sabor | q04, q07, q14–q18, q22 |
| preco | q08, q24 |
| tempo_entrega | q09–q13, q20 |

A tabela fixa pelo texto da pergunta o aspecto das 24 respondíveis de
`human-v2`. Todas as 24 entram na média principal, inclusive as paráfrases.
A saída do extrator não participa dessa seleção. Aplicar o filtro apenas a
perguntas de reclamação com aspecto mapeado na taxonomia, sempre com
`aspect_<nome>=neg`. Sem aspecto aplicável ou com aspecto fora da taxonomia,
desligar o filtro de aspecto. q25–q28 ficam fora da média principal e são
controles sem ação do filtro. q29 (sabor) e q30 (tempo_entrega) são controles
negativos separados com aspecto mapeado, item inexistente e janela sem
reviews, respectivamente.

### Comparação e critério de sucesso

Usar a mesma coleção enriquecida, o corpus congelado de 100 reviews, os mesmos
embeddings multilíngues, texto, chunking, filtros de restaurante, item e data,
e o limiar operacional de 0,25 nos dois braços. O único fator que muda é
acrescentar o filtro de aspecto negativo. Fixar k=5 como análise principal e
k=8 como diagnóstico. Não acionar fallback sem aspecto nesta comparação,
pois ele esconderia perdas do filtro.

Calcular as métricas pelas definições já registradas: hit@k, precision@k
(divisor k mesmo com posições vazias), recall@k limitado e MRR truncado em k.
Manter os mesmos IDs relevantes nos dois braços. Reportar as contagens,
médias e vitórias, empates e derrotas pareadas por pergunta para precisão e
recall. Nos controles negativos, registrar quantas consultas retornam vazio.

Considerar a hipótese apoiada neste conjunto se o filtro ganhar pelo menos
2 pontos percentuais de precision@5, perder no máximo 2 pontos percentuais
de recall limitado@5 e transformar em zero acertos no máximo uma pergunta
que tinha evidência no top 5 sem o filtro. Esses limites são operacionais.
Reportar todas as diferenças mesmo se o critério não for atingido.

Antes do ranking, contar os pares pergunta–review relevante que passam pelos
filtros básicos e são excluídos pelo ABSA. Separar saída inválida, aspecto
ausente e polaridade positiva. Reportar também quantas perguntas perdem todos
os seus relevantes elegíveis. Ler os casos de perda para distinguir erro do
extrator de divergência de anotação ou de escopo. Essa auditoria complementa
a métrica de recall, que só vê os itens retornados no top k.

### Quatro braços e leitura das contagens

| Braço | Restrição de aspecto | Fonte dos rótulos |
| --- | --- | --- |
| A | Desligada. Referência v0.1. | Nenhuma para a consulta |
| B | Negativo, filtro estrito | Predições QLoRA |
| C | Negativo, filtro estrito | Rótulos do gerador, controle idealizado |
| D | Negativo, filtro estrito | Rótulos humanos congelados do gold |

O braço D está confirmado: os 100 IDs e textos de `human-v2` correspondem
ao gold cego, e os mesmos 100 IDs constam em
`data/gold/aspects_100.human.jsonl`. Juntar os rótulos humanos por ID.
Para o braço C, juntar por ID com a origem sintética versionada e conferir
a correspondência dos textos. Usar coleções com os mesmos vetores, chunks,
escopo e limiar. Manter os IDs relevantes congelados nos quatro braços.
Comparar B, C e D com A e reportar também as diferenças entre os filtros.
O critério de sucesso pré-registrado vale para B versus A. C e D servem
para interpretar o resultado e a influência da fonte dos rótulos.

O controle é uma referência idealizada para os rótulos sintéticos, sem
garantia de teto numérico para cada métrica. Parte da relevância se apoia
nos mesmos aspectos que orientam o gerador. Se os filtros empatarem,
atribuir o ganho à ideia de filtrar por aspecto neste benchmark, sem
atribuir o resultado à qualidade do extrator em texto real.

Todas as 24 perguntas respondíveis têm aspecto mapeado. Nas que usam
paráfrase, o aspecto vem da intenção registrada na tabela. Informar
`24/24` na análise principal e manter q29 e q30 como controles separados.
Publicar os numeradores em 120 posições no top 5 por braço, os IDs
relevantes recuperados e o placar por pergunta, inclusive as perdas de
evidência. Cada acerto líquido em 120 posições vale cerca de 0,83 ponto
percentual de precision@5. O critério já fixado de pelo menos 2 pontos
percentuais exige três acertos líquidos adicionais.

### Fallback quando a extração falha

Contar quantas das 100 reviews ficam sem aspectos por saída inválida e
quantas produzem um mapa vazio válido. Contar por ID de review, mesmo
quando o índice tiver vários chunks. Uma saída inválida não informa se
o aspecto está presente.

Na consulta operacional com filtro de aspecto, se houver ao menos uma
review com `absa_status=error` no escopo dos filtros básicos, executar
a busca sem a restrição de aspecto, preservando restaurante, item,
período, limiar e k. Registrar o motivo do fallback e reportar quantas
consultas acionam a regra. A presença de um erro, mesmo com resultados
válidos no top k, é suficiente para acionar o fallback. Um mapa vazio
válido sozinho não aciona a regra. Medir o fallback separadamente dos
braços estritos para manter visível a exclusão de evidência.

### Escopo e próxima versão

O corpus sintético de `human-v2` serve para validar o enriquecimento.
As perguntas já orientaram iterações anteriores. A avaliação é
exploratória e o comportamento em reviews reais de restaurante é
desconhecido.

Adiar o treino de uma segunda versão com exemplos fora de domínio e
mapas vazios. A avaliação de uma versão futura exige um novo conjunto
anotado e reservado antes do treino. Os 30 textos B2W anotados ficam
fora do treino. Priorizar integração, notebook Kaggle, artigo, Docker
e catálogo de replay.
