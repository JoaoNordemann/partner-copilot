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
- O conjunto de referência tem 100 anotações por IA, pendentes de revisão humana;
  os aspectos sintéticos emitidos pelo gerador não substituem anotação humana.

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

## Splits e prevenção de vazamento

O corpus bruto em `data/raw/` permanece integral e sem alteração. Os splits derivados
são versionados em `data/splits/`, separados dos dados públicos de `data/external/`.
O guia de anotação permanece em `docs/annotation-guide.md`, sem alterar o snapshot anotado.

| Destino | Registros | Rótulos e uso |
|---|---:|---|
| `gold.jsonl` | 100 | Anotações por IA, pendentes de revisão humana; avaliação |
| `train_pool.jsonl` | 2037 | Rótulos sintéticos do gerador; treino de ABSA |
| `rag.jsonl` | 862 | Reviews reservadas exclusivamente ao índice RAG |
| `quarantine.jsonl` | 1 | Duplicata textual do gold, sem treino nem RAG |

Seed da separação: `2718`. Após reservar os 100 IDs de avaliação e todas as suas
duplicatas normalizadas, 70% dos grupos textuais restantes vão para treino e 30%
para RAG. A proporção aplica-se a grupos, não diretamente ao número de linhas;
por isso as contagens não correspondem necessariamente a uma divisão exata 70/30.
A normalização usa casefold e compactação de espaços, preservando acentos.
Todos os restaurantes e todas as notas estão representados nos três splits principais.

A reserva contém 101 IDs: os 100 anotados e uma duplicata textual. Não se atribui
anotação adicional à duplicata em quarentena. Os conjuntos principais são disjuntos
por ID e texto normalizado; os 3000 registros originais estão contabilizados.
O manifesto registra todos os IDs e hashes SHA-256 do conteúdo com quebras LF,
permitindo verificação independente da convenção de fim de linha do sistema.

`load_absa_train_pool()` valida integridade, partições, IDs e textos reservados antes
de retornar qualquer exemplo. É a entrada definida para o futuro treinador de ABSA.
Os testes injetam deliberadamente um texto do gold sob outro ID e confirmam a rejeição.
Ainda não há treino QLoRA implementado; código futuro precisa usar esse carregador.

A ingestão padrão usa `DATA_SPLITS_DIR/rag.jsonl`, verifica o manifesto antes de carregar
embeddings e recusa o corpus bruto integral ou o pool de treino como entrada. Uma coleção
Chroma já populada com IDs fora do RAG também é recusada, pois upsert não remove documentos
antigos. Nesse caso, configurar uma nova `CHROMA_COLLECTION`; não apagar dados automaticamente.

```powershell
python scripts/prepare_data_splits.py
python scripts/prepare_data_splits.py --check-only
python scripts/ingest.py --batch-size 128
```

Mudanças no corpus ou nas anotações congeladas exigem revisão explícita dos snapshots e
recriação dos splits. A ausência de vazamento literal não garante independência entre
famílias de templates: o corpus ainda é sintético. O gold atual não deve ser apresentado
como benchmark humano independente até a revisão correspondente.

## Ingestão, IDs e chunking

A CLI usa a pipeline tolerante em `ingestion/pipeline.py`. IDs autoritativas são preservadas;
`review_id` é aceito como alias de entrada. Sem ID, usa SHA-256 de restaurante/data/texto.
Reviews que cabem no contexto do embedder são documentos únicos; textos maiores são
janelas de tokens com overlap de 16, descontando tokens especiais e prefixos E5.
O limite de segurança por review é 50000 caracteres, configurável.

Chunks possuem IDs determinísticas por fonte/índice e guardam a ID original para citações.
Chunks obsoletos são removidos somente após a gravação completa da review atualizada.
O pipeline reporta contagens reais de documentos novos/existentes e ignora registros inválidos,
mas falhas de infraestrutura e de integridade interrompem o processo. Reexecução é idempotente.
Os contratos congelados de gold/treino/RAG não foram alterados. Regras completas em
`docs/ingestion.md`.

## CLI e reset explícito

O script de entrada limita-se a parsing, configuração e apresentação. A orquestração
passou para `ingestion/service.py`. Flags de dados, banco, modelo e batch sobrescrevem
os defaults conforme aplicável, sem alterar a configuração global em cache.

`--reset` autoriza limpar somente a collection do store selecionado, após validar os splits
e preparar modelo/tokenizador. O modo padrão não apaga documentos e rejeita collections
com IDs fora do RAG. O reset explícito permite reconstruir essa collection sem afetar outras.
Falhas após a exclusão não são transacionais; a reexecução continua idempotente.

## Contrato de resposta e abstenção

As decisões anteriores à implementação do retorno estruturado, marcador
[[SEM_EVIDENCIA]], caminhos de abstenção e context_k=5 estão registradas em
[docs/decisions.md](docs/decisions.md#contrato-de-resposta-abstenção-e-contexto-da-geração).
O contrato é alvo de implementação; sua documentação não afirma que já foi codificado.
