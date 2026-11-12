# Estudo de Engenharia de IA: status

Atualizado com os resultados do filtro por aspecto, da avaliação externa e da latência isolada do QLoRA.

| Frente | Estado | Evidência / próximo passo |
| --- | --- | --- |
| Fundamentos HF e inferência NF4 | Concluído no escopo estudado | PoCs informadas e execuções Kaggle preservadas |
| Schema, configuração e dados sintéticos | Implementado e testado | Testes Pydantic/gerador; data/raw versionado |
| Gold, guia de anotação e splits | Referência humana congelada | 100 reviews anotadas pelo autor com adjudicação assistida e exposição prévia documentada. [Manifesto](../data/gold/human_review_manifest.json) |
| Ingestão e persistência | Implementado e testado | IDs determinísticos, Chroma temporário nos testes, bootstrap CPU verificado |
| Retrieval e baselines | Medido | Com/sem filtros, embeddings, k e placares em RESULTADOS.md |
| Geração v3 e análise de falhas | Medido, com limitações | n12/n15/n16 e rubrica; prompt/parser congelados |
| API | Implementado e testado | Startup, modos, saúde, fila, timeout e testes sem GPU |
| Demo Gradio | Implementado e verificado localmente | HTTP com API fake e inspeção visual; fontes integrais e exemplos gravados |
| Latência CPU isolada | Medida | reports/api-cpu-latency-v1; hardware explícito |
| Docker CPU | Receita e bootstrap prontos; container não verificado | Reservar até uma hora nas janelas de treino QLoRA para iniciar o Docker, construir a imagem e testar o container |
| Replay aprovado | Contrato e testes prontos; catálogo pendente | Até três casos com aprovação humana elegível. Começar pela resposta n17 e pela abstenção n20. A falha n12 fica na aba histórica |
| CI e versão MVP | Implementado; publicação protegida por gate | Tag v0.1-rag-mvp somente após CI remoto verde no mesmo commit; badge do README |
| QLoRA / ABSA | Treino concluído | 759 passos na T4, checkpoint 253 escolhido pela validação. 140/140 JSONs válidos na validação. Gold e templates reservados medidos uma vez. [Avaliação](../reports/absa-eval-checkpoint-253-v1/README.md) |
| Avaliação externa B2W | Medida | 9/30 mapas exatos em e-commerce. Validade estrita de 172/200. [Relatório](absa-external-evaluation.md) |
| Adapter ABSA | Publicado e verificado | Download anônimo em sessão limpa no Kaggle, com 3/3 exemplos sintéticos válidos e exatos. [Model card](absa-model-card.md) |
| Integração ABSA na ingestão | Publicada e desligada por padrão | Tag `v0.2-aspects` no commit `69b448f`, aprovado pelo CI. [CI do commit da tag](https://github.com/JoaoNordemann/partner-copilot/actions/runs/42930288620) |
| Retrieval com aspecto | Medido em CPU | 37/120 → 45/120 relevantes no top 5 com QLoRA. Teto de 55/120. [Relatório](../reports/absa-retrieval-v1/README.md) |
| Latência isolada do QLoRA | Medida em Tesla T4 | 30 reviews em lote unitário após aquecimento. Mediana de 1,41 s, p95 de 2,38 s e pico de 1,17 GiB alocados. [Medição](absa-external-evaluation.md#baselines-complementares-e-transferência) |
| FP16 na T4 16 GB | Medido | Completou 36/36 chamadas. A menor leitura após geração foi de 49 MiB livres. [Relatório](../reports/mistral-t4-v1/README.md) |
| API real ponta a ponta | Medida | NF4 na T4, 20 chamadas sequenciais e duas simultâneas. [Relatório](../reports/mistral-t4-v1/README.md#api-ponta-a-ponta) |
| Space | Adiado | Não bloquear entrega local; distinguir gravação de busca CPU ao vivo |
| Avaliação final reservada | Preservada, não executada | Uma rodada futura, sem ajuste posterior |

## Resultados do ABSA

| Conjunto | QLoRA, acerto exato | Melhor baseline por acerto exato |
| --- | ---: | ---: |
| Gold sintético | 85/100 | TF-IDF, 60/100 |
| Templates reservados | 340/346 | TF-IDF, 101/346 |
| Famílias inéditas dentro dos reservados | 36/36 | TF-IDF, 22/36 |
| B2W com rótulos humanos | 9/30 | Regras, 23/30 |

Na B2W, o QLoRA produziu 172/200 JSONs válidos. Nos 30 textos anotados,
acertou 9 pares, previu 20 pares extras e omitiu 3. Em 13/100 reviews do
gold, reproduziu a convenção do gerador onde ela divergia do guia humano.
A amostra externa tem um único anotador e é de e-commerce, o que limita
a extrapolação para reviews reais de restaurantes.
[Resultados e baselines](absa-model-card.md#resultados) ·
[Protocolo e revisão B2W](absa-external-evaluation.md)

A referência B2W versiona os IDs, os rótulos e seu manifesto. Os textos
integrais ficam locais, conforme a política de distribuição do projeto.
[Rótulos](../data/absa/b2w-human-v1.jsonl) ·
[Origem e licença](external-data.md)

No retrieval com aspecto, a precision@5 passou de 30,83% para 37,50%,
com teto de 45,83% (55/120). O recall limitado@5 subiu de 73,13% para
84,86%, com 7 vitórias, 17 empates e nenhuma derrota. QLoRA e gerador
empataram nos rankings, com convenção de relevância compartilhada,
corpus sintético e perguntas já vistas.
[Resultados por pergunta](../reports/absa-retrieval-v1/README.md)

Nos textos B2W com aspecto anotado, QLoRA e regras empataram em 6/11.
Nos vazios, foram 3/19 para o QLoRA e 17/19 para as regras. A validade
sintática foi 199/200. A medição isolada do QLoRA na T4 incluiu
tokenização, inferência e decodificação com o modelo já carregado.
[Avaliação externa e latência](absa-external-evaluation.md)

## Custos medidos na T4

| Ambiente e conjunto | Modo | n | Pico alocado / reservado | Latência mediana / máxima | Mediana de tokens/s |
| --- | --- | ---: | ---: | ---: | ---: |
| Kaggle, T4 16 GB, originalmente limpo | NF4 | 9 | 4,53 / 5,00 GiB | 5,64 / 20,54 s | 13,24 |
| Kaggle, T4 16 GB, originalmente limpo | FP16 | 9 | 14,16 / 14,31 GiB | 9,07 / 22,50 s | 9,23 |
| Kaggle, T4 16 GB, contaminado | NF4 | 27 | 4,68 / 6,31 GiB | 15,72 / 38,50 s | 13,49 |
| Kaggle, T4 16 GB, contaminado | FP16 | 27 | 14,32 / 14,38 GiB | 20,45 / 52,90 s | 9,33 |

Na API real com NF4 na T4 e retrieval em CPU, as 20 requisições do conjunto
contaminado tiveram mediana de 24,07 s e máximo de 39,62 s. Oito
retornaram HTTP 200 e 12 retornaram HTTP 502 por contrato de saída.
No par simultâneo, a segunda requisição esperou 5,71 s.
[Relatório e ambiente da medição](../reports/mistral-t4-v1/README.md)

## Plano de GPU

Em 2026-11-09, o painel de opções da sessão do Kaggle exibiu
`Quota: 01:25 / 30 hrs` com GPU T4 x2 selecionada. O orçamento abaixo usa
85 minutos como saldo observado. Conferir novamente antes de iniciar.

| Trabalho | Teto de sessão | Condição |
| --- | ---: | --- |
| Comparação FP16 e NF4 com API real | 34 min 50 s de sessão | Concluída em uma T4. O teto era de 35 min, com 88 min de cota antes da partida. |
| Experimento ABSA no retrieval | 0 min de GPU | Concluído em CPU com as predições congeladas. |
| Reserva | 25 min | Download, indisponibilidade de hardware ou repetição de uma etapa que falhe. |

A referência para o enriquecimento em lote unitário é a mediana de
1,41 s por review na T4, com p95 de 2,38 s e pico de 1,17 GiB alocada.
Extrapolar a mediana dá cerca de 2 a 3 minutos para 100 reviews e
70 minutos para 3.000, além de carga, download e I/O. Essas projeções
servem ao planejamento. A avaliação reutilizou as predições das
100 reviews. Reservar uma janela própria para o corpus
de 3.000 se for necessário indexá-lo com ABSA.
[Latência isolada](absa-external-evaluation.md#baselines-complementares-e-transferência)

Preparar entradas e comandos localmente antes de iniciar cada sessão.

## Distribuição das pendências

- **Docker CPU:** construir a imagem e verificar o container localmente em uma janela sem dependência de GPU.
- **Refatoração e publicação:** priorizar refatoração, README e publicação do projeto.
  A curadoria do MVP tem teto de três entradas de replay aprovadas. Os três exemplos
  históricos já cobrem o roteiro da demo, incluindo a falha conhecida.
- **Space:** manter adiado e reavaliar quando houver tempo e catálogo elegível.

[Resultados e limitações](../reports/final-results-v1/RESULTADOS.md) ·
[Notas da versão](releases/v0.1-rag-mvp.md) · [Decisões](decisions.md)
