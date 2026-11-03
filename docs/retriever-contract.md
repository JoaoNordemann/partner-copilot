# Contrato do retriever

O store exige coleção com `hnsw:space=cosine`. A distância retornada pelo Chroma
é convertida em `score = 1 - distância`, isto é, similaridade de cosseno.
O intervalo teórico é [-1, 1]: 1 para vetores paralelos, 0 para ortogonais e -1
para opostos. O score não é probabilidade nem confiança calibrada. Com L2 ou outra
métrica, subtrair a distância de 1 não teria esse significado; o store rejeita a coleção.

O retriever pede até `2 * k` candidatos (limitados pelo tamanho do índice), mantém
`score >= min_score` e retorna no máximo `k`, na ordem do Chroma. Se poucos
passarem, devolve menos; se nenhum passar, devolve `[]`. Nunca reduz o limiar
nem relaxa os filtros para completar a lista. Os defaults vêm de `Settings`.

A margem de candidatos permite etapas futuras de reranking/deduplicação. Hoje,
com apenas ordenação por cosseno e corte por limiar, ela não melhora o top-k em
relação a pedir k candidatos. Também não garante recall de uma busca aproximada.
Os resultados são documentos/chunks; não há deduplicação por review nesta camada.

`restaurant_id` é obrigatório. Um único filtro vira `{"restaurant_id": "rest_001"}`.
Vários filtros viram `{"$and": [...]}`. O Chroma aplica os filtros na busca, antes
do corte local por score. `aspect="tempo_entrega"` exige `aspect_tempo_entrega="neg"`;
logo exclui avaliações positivas ou que não mencionam esse aspecto. Categoria,
cidade e bairro são comparações exatas opcionais.

Datas de origem continuam ISO, mas limites usam exclusivamente o metadado inteiro
`created_at_int` (YYYYMMDD). `start_date` vira `$gte`; `end_date`, `$lte`; ambos são
inclusivos e formam duas cláusulas separadas em `$and`. Limites unilaterais são aceitos;
janela invertida falha antes de consultar o banco. Índices antigos sem esse metadado
precisam de reingestão. Alterar apenas o schema não migra os registros persistidos.

```python
from datetime import date, timedelta

end = date(2026, 11, 1)  # Data explícita do snapshot, não o relógio atual.
docs = retriever.retrieve(
    "por que as notas de entrega caíram?",
    "rest_002",
    start_date=end - timedelta(days=13),  # 14 datas incluindo o limite final.
    end_date=end,
)
```

A pipeline aceita os mesmos filtros temporais e devolve uma resposta de abstenção
com fontes vazias quando o retriever retorna `[]`, sem chamar o LLM. Ela não interpreta
automaticamente “últimas duas semanas” no texto: o chamador deve fornecer a janela.
Para investigar uma queda, comparar períodos e distribuições de notas continua sendo
necessário; reviews recuperadas por similaridade não provam uma tendência estatística.

Os testes em `tests/test_retriever.py` verificam o limiar inclusivo, `2*k`, a conversão
de filtros, os limites de data, isolamento por restaurante, scores conhecidos
(1/0/-1), rejeição de métrica incompatível e abstenção sem inferência.
