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

- `data/raw/reviews.jsonl`: `9a7326c32fdeef5f012e2be828728b2c630713c591de8cf44ef022b812c0707f`
- `data/raw/restaurants.json`: `32d1fccdfcff8e165b8264417f163876b21c81c9106367bd7921e1301fc10d24`

O gerador usa a convencao de quebras de linha da plataforma. Para comparar
conteudo entre plataformas, normalize CRLF/LF ou compare os objetos JSON;
os hashes acima registram os arquivos produzidos no Windows nesta execucao,
antes de eventual normalizacao de quebras de linha pelo Git.
