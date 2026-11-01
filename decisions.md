# Decisoes do PartnerCopilot

## 2026-11-01 - Dataset sintetico de referencia

- Gerador: `scripts/generate_synthetic_data.py`.
- Quantidade: 3000 reviews de 8 restaurantes, 100% sinteticos.
- Seed: `42`.
- Data final fixa: `2026-11-01`.
- Janela historica: `90` dias (2026-08-04 a 2026-11-01, inclusive).
- Tendencia: piora de tempo de entrega nos ultimos 14 dias, nos restaurantes
  configurados com `late_trend=True` (2026-10-19 a 2026-11-01, inclusive).
- Validacao: todos os registros passaram pelo schema `Review`.
- Dados brutos preservam `created_at` como string ISO. O schema interpreta a data
  e deriva `created_at_int` em YYYYMMDD para metadados e filtros do Chroma.
- Os dois arquivos brutos sao versionados como referencia para auditoria e gold set.
  Indices Chroma, caches e demais artefatos gerados continuam ignorados pelo Git.
- O gold set ainda precisa ser selecionado e anotado; os aspectos sinteticos
  emitidos pelo gerador nao substituem anotacao humana.

### Comando de reproducao

```powershell
python scripts/generate_synthetic_data.py --n 3000 --seed 42 --end-date 2026-11-01 --days 90 --validate
```

A seed sozinha nao fixa o dataset: mantenha tambem data final, janela e versao
do gerador. O default dinamico `date.today()` nao deve ser usado nesta referencia.

### Integridade dos arquivos (SHA-256 dos arquivos gerados no Windows)

- `data/raw/reviews.jsonl`: `c8cc49f3971ad9ace7896f4ec5065fcb9b2c221f55c5d51b46272f321e03b642`
- `data/raw/restaurants.json`: `32d1fccdfcff8e165b8264417f163876b21c81c9106367bd7921e1301fc10d24`

O gerador usa a convencao de quebras de linha da plataforma. Para comparar
conteudo entre plataformas, normalize CRLF/LF ou compare os objetos JSON;
os hashes acima registram os arquivos produzidos no Windows nesta execucao,
antes de eventual normalizacao de quebras de linha pelo Git.

## Auditoria e revisão da linguagem sintética

A auditoria está em `docs/data-audit.md`, incluindo 50 exemplos anteriores, 50 revisados,
contagens de repetição, distribuição de notas e contagens semanais de atraso.
A referência mantém n=3000, seed=42, end-date=2026-11-01 e days=90, com a versão revisada
do gerador. Os textos e alguns atributos amostrados mudaram; o hash acima corresponde
à referência revisada, não ao corpus anterior.

A temperatura esperada agora depende do item, a linguagem de sabor evita contradições
entre doces e salgados, e avaliações negativas têm limites de nota e conclusões compatíveis.
O acréscimo de negatividade de sabor de rest_007 foi alterado de 0,05 para 0,15 para
representar um ponto fraco observável. Os demais pontos fracos e a probabilidade de atraso
recente (0,75) foram mantidos. População e linguagem usam fluxos aleatórios separados.

O corpus permanece baseado em templates e não substitui um gold set independente com
anotação humana. Duplicatas e famílias de templates precisam ser consideradas na separação
de treino e avaliação. Índices já gerados a partir dos textos anteriores exigem novo upsert.
