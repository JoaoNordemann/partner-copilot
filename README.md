# PartnerCopilot

[![CI](https://github.com/JoaoNordemann/partner-copilot/actions/workflows/retriever-unit.yml/badge.svg)](https://github.com/JoaoNordemann/partner-copilot/actions/workflows/retriever-unit.yml)

Ajuda parceiros de restaurantes a investigar avaliações em linguagem natural,
com fontes e abstenção quando falta evidência. Projeto de portfólio com **dados
sintéticos**, sem dados reais ou vínculo oficial com o iFood.

## Rodar em CPU: três comandos

Na raiz do clone, com Python 3.12 ou 3.13 e ambiente virtual ativo:

```powershell
python -m pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.2,<3"
python -m pip install -r requirements-cpu.txt "gradio>=6,<7" "httpx>=0.27,<1"
python scripts/run_mvp.py
```

Abrir [demo](http://127.0.0.1:8000/demo/) ou [API](http://127.0.0.1:8000/docs).
O primeiro uso baixa o encoder multilíngue e reconstrói o índice RAG; reinícios
reutilizam o banco. O padrão é **LLM fake: abstenção fixa, rotulada como simulação**.
A aba histórica mostra sucesso, abstenção e falha n12, todos como respostas gravadas.
Replay exige catálogo aprovado externo; não há um catálogo pronto incluído.
**Geração real com Mistral NF4 requer GPU CUDA** e segue [instruções próprias](docs/demo.md).

## Testar

```powershell
python -m pip install -r requirements-ci.txt
python -m pip install --no-deps -e .
python -m pytest -m "not gpu"
python -m ruff check .
python -m ruff format --check .
python scripts/build_results.py --check --update-readme
```

A suíte completa usa Chroma/encoder fake, sem downloads; os testes semânticos são
opt-in. CI mínimo usa seleção explícita sem runtime ML, Python 3.12 e 3.13.

## Arquitetura em cinco linhas

1. Reviews Pydantic e splits versionados separam gold, treino e índice RAG.
2. Ingestão valida dados, divide textos longos e faz upsert idempotente no Chroma persistente.
3. Embeddings multilíngues e filtros recuperam contexto por restaurante, data, aspecto e item.
4. Geração v3 produz JSON; validação confere esquema, IDs e trechos literais, com abstenção.
5. FastAPI gerencia recursos/concorrência; Gradio mostra afirmações e reviews completas lado a lado.

## Resultados

<!-- BEGIN GENERATED RESULTS -->
- RAG de reviews sintéticas, com citações verificadas e abstenção; sem dados reais do iFood.
- Retrieval: recall limitado@5 sem filtro de 0,2514 no multilíngue e 0,2583 no inglês; 4V/16E/4D em 24 perguntas respondíveis expostas.
- Geração v3: 6/9 saídas aceitas, incluindo duas abstenções; 3/4 substantivas aceitas sustentadas e pertinentes na leitura de IA.
- Retry descartado: 25 chamadas extras, 0 rejeições recuperadas; formato válido não garante resposta correta.
- Evidência limitada por corpus conhecido, amostras pequenas e revisão humana assistida.

[Resultados, tabelas e limitações](reports/final-results-v1/RESULTADOS.md).
<!-- END GENERATED RESULTS -->

- **Geração v3 no Kaggle, Tesla T4 com NF4:** mediana 6,3 s, máximo observado 31,9 s
  (9 chamadas). [Medições de geração](reports/cost-latency-consolidation-v1/README.md)
- **Embedding + busca em CPU, Ryzen 5 5600:** mediana 17,8 ms e p95 19,8 ms
  (40 amostras), com o modelo já carregado e índice RAG de 862 reviews.
  A medição local tem escopo restrito a esse índice e hardware. Extrapolar
  para produção exige medir com volume e carga representativos.
  [Medições em CPU](reports/api-cpu-latency-v1/README.md)

Em T4 de 16 GB, o Mistral 7B em 4 bits usou **4,53 GiB de pico alocado**
e respondeu em **5,64 s** (mediana, n = 9, conjunto originalmente limpo).
Em FP16, coube com **14,16 GiB de pico alocado** e mediana de **9,07 s**
no mesmo conjunto. [Comparação na mesma T4](reports/mistral-t4-v1/README.md)

## Limitações

Formato válido e trecho literal não garantem resposta correta: n12 seleciona elogio
ignorando crítica; n15 atribui trecho à review errada; n16 combina relatos distintos.
Amostras pequenas, sintéticas e perguntas expostas limitam as conclusões; revisões
humanas são assistidas. O Space está pendente.

O QLoRA ABSA foi treinado. O checkpoint 253 teve a menor perda teacher-forced
entre os três checkpoints avaliados, na primeira época. Na validação, 84,1%
das ocorrências de frases normalizadas aparecem no treino. No gold, são 70,4%.
A avaliação de generalização dentro do corpus sintético usa os templates
reservados, com um recorte de 36 reviews compostas só por famílias inéditas.
JSON válido em 140/140 na validação. O QLoRA obteve macro-F1 de 0,9819 no gold
(100 reviews), 0,9948 nos templates reservados (346) e 1,0000 no recorte de
36 reviews inteiramente inéditas dentro do gerador. O TF-IDF obteve 0,8688,
0,7240 e 0,3980, respectivamente.
[Relatório do treino ABSA](reports/absa-qlora-train-v1/README.md) ·
[Avaliação ABSA](reports/absa-eval-checkpoint-253-v1/README.md).

Na B2W, a validade estrita do adapter foi 172/200 e a sintática, 199/200.
Nos textos de e-commerce com rótulo, adapter e regras empataram em 6/11.
Nas referências vazias, foram 3/19 para o adapter e 17/19 para as regras.
As regras e partes do pipeline foram escritas com assistência de IA.
O autor revisou os resultados.
[Relatório B2W](docs/absa-external-evaluation.md) ·
[Adapter e model card no Hugging Face](https://huggingface.co/jnordemann/partnercopilot-absa-qlora-v1).
[Docker CPU](docs/docker.md) está preparado, mas build/execução não foram testados
localmente por falta de Docker; o caminho GPU em container também não foi testado.

[Notas v0.2-aspects](docs/releases/v0.2-aspects.md) · [Notas v0.1-rag-mvp](docs/releases/v0.1-rag-mvp.md) · [Status do estudo](docs/study-status.md) ·
[Demo](docs/demo.md) · [API](docs/api.md) · [Decisões](docs/decisions.md)
