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
