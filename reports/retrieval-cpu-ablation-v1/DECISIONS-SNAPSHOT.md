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
