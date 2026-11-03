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
