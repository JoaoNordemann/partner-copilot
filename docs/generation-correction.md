# Abstencao diagnostica e correcao unica

Prompt v2 e parser v2 permanecem congelados. D e um experimento adicional,
correction-v1, sem alterar a pipeline de producao ou aceitar recusas tolerantes.

## Definicoes

- Estrita: texto bruto, apos strip, igual a [[SEM_EVIDENCIA]].
- Tolerante: marcador literal presente e nenhuma citacao valida. Uma citacao valida
  e um token [id] cujo conteudo inteiro coincide com um ID do contexto. Uma lista
  [id1, id2] nao e token valido. Recusas em linguagem livre sem marcador nao contam.
- Reportar separadamente texto bruto e texto apos normalizar barra + underscore.
- Abstencoes retriever_empty nao sao chamadas do LLM. Taxas de pipeline incluem
  esses casos, mas as taxas de LLM usam somente as chamadas ao modelo.
- Tolerante e apenas diagnostica: pode aceitar como recusa um texto com afirmacoes
  sem suporte, IDs mal formatados ou ate conteudo contraditorio. Nao e aval factual.

## Resultados dos arquivos recebidos (texto bruto)

| Medida | v1 estrita | v1 tolerante | B/v2 estrita | B/v2 tolerante |
| --- | --- | --- | --- | --- |
| Abstencao nas 6 negativas, incluindo retrieval vazio | 2/6 | 6/6 | 2/6 | 2/6 |
| Abstencao nos 4 negativos com LLM (q25-q28) | 0/4 | 4/4 | 0/4 | 0/4 |
| Abstencao nas 24 respondiveis, incluindo retrieval vazio | 1/24 | 16/24 | 1/24 | 6/24 |

O 0/4 tolerante da v2 nao contradiz a leitura qualitativa de recusas: o modelo
substituiu o marcador por frases livres. A regra pedida nao reconhece essas frases.
A v1 tolerante tambem revela muita recusa em perguntas respondiveis; nao reportar
apenas o ganho nas negativas. O diagnostico normalizado e salvo em outra visao.

```bash
python scripts/analyze_generation_abstention.py --source /caminho/B.jsonl --output /caminho/B-abstention.json
```

Nao sobrescreve origem ou relatorio existente. Mantem as taxas e erros originais.

## Experimento D

Usa B como origem; aplica parser-v2 para reconstruir o baseline C. Mantem pergunta,
contexto e parametros de geracao. Apenas saidas rejeitadas recebem UMA chamada com
a mensagem do erro e a resposta anterior escapada como dado. Nao refaz retrieval.
No artefato recebido, C aceita 2 das 27 saidas, logo D pode pedir ate 25 correcoes,
nao 30 novas primeiras respostas. Falha de runtime nao recebe outra tentativa.

```bash
python scripts/evaluate_generation_retry.py --source /caminho/B.jsonl --output /caminho/D.jsonl --check-only
python scripts/evaluate_generation_retry.py --source /caminho/B.jsonl --output /caminho/D.jsonl --resume
```

A execucao real exige CUDA e o HF_TOKEN do ambiente. get_llm carrega uma vez no
processo. O arquivo D tem uma linha final por pergunta e attempts com as duas
saidas. D.jsonl.attempts.jsonl e um ledger duravel de tres eventos por pergunta:
primeira tentativa, inicio da correcao e resultado. O primeiro registro e gravado
antes da chamada. Se a sessao cair depois do evento de inicio, sem resultado,
a retomada marca interrupted_unknown e nao repete a chamada. Isso evita novas
tentativas escondidas; pode exigir outro experimento para medir o caso interrompido.
Preserve ambos JSONLs junto com o resumo. Erros de formato na segunda resposta
continuam sendo falhas; nao existe terceira tentativa.

Cada tentativa mantem metricas proprias. latency_ms de D e a soma do tempo historico
de B com a correcao, nao um benchmark de uma execucao continua; use source_latency_ms,
correction_latency_ms e as metricas de cada tentativa para analise de custo/VRAM.

v2 foi criada depois de ver a v1 nas mesmas 30 perguntas. D tambem e adaptacao de
desenvolvimento sobre elas; nao e teste independente. Nenhuma inferencia real de D
foi executada no PC sem CUDA. Notebooks antigos e seus experimentos A/B/C permanecem
preservados. O notebook partner-copilot-D.ipynb e separado e exige que o codigo novo
esteja disponivel no GitHub antes de clonar no Kaggle.
