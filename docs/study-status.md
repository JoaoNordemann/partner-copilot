# Estudo de Engenharia de IA: status

Atualizado em 2026-11-09 com os resultados externos do ABSA e o plano de GPU.

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
| Avaliação externa B2W | Medida | 30 IDs e rótulos congelados, com teste de formato em 200 textos. [Relatório](absa-external-evaluation.md) |
| Adapter ABSA | Publicado e verificado | Download anônimo em sessão limpa no Kaggle, com 3/3 exemplos sintéticos válidos e exatos. [Model card](absa-model-card.md) |
| Integração ABSA na ingestão | Protocolo registrado | Implementação e avaliação exploratória pendentes. [Decisões](decisions.md#enriquecimento-absa-na-ingestão--desenho-e-protocolo-exploratório) |
| FP16 na T4 16 GB | Pendente | Comparar o Mistral FP16 e NF4 com a mesma entrada e configuração de geração |
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

## Plano de GPU

Em 2026-11-09, o painel de opções da sessão do Kaggle exibiu
`Quota: 01:25 / 30 hrs` com GPU T4 x2 selecionada. O orçamento abaixo usa
85 minutos como saldo observado. Conferir novamente antes de iniciar.

| Trabalho | Teto de sessão | Condição |
| --- | ---: | --- |
| Comparação FP16 e NF4 | 35 min | Uma T4 de 16 GB, mesma revisão do Mistral e mesmas entradas. Fazer um teste curto de carga em FP16 na GPU 0 e registrar eventual falta de memória. |
| Enriquecimento ABSA | 25 min | GPU 0 para extrair os aspectos das 100 reviews do corpus congelado e exportar as previsões. Construir o índice e comparar os filtros em CPU. |
| Reserva | 25 min | Download, indisponibilidade de hardware ou repetição de uma etapa que falhe. |

A referência para o enriquecimento em lote unitário é a mediana de
1,41 s por review na T4, com p95 de 2,38 s e pico de 1,17 GiB alocada.
Extrapolar a mediana dá cerca de 2 a 3 minutos para 100 reviews e
70 minutos para 3.000, além de carga, download e I/O. Essas projeções
servem ao planejamento. O teto de 25 minutos cobre a sessão para as
100 reviews de avaliação. Reservar uma janela própria para o corpus
de 3.000 se for necessário indexá-lo com ABSA.
[Latência isolada](absa-external-evaluation.md#baselines-complementares-e-transferência)

Preparar entradas e comandos localmente antes de iniciar cada sessão.
Medir latência após aquecimento e pico de VRAM na comparação FP16/NF4.
Se a carga FP16 falhar, registrar o erro e preservar o saldo da integração.

## Distribuição das pendências

- **Docker CPU:** construir a imagem e verificar o container localmente em uma janela sem dependência de GPU.
- **Na próxima sessão Kaggle que tiver folga:** aproveitar a mesma sessão de outro
  trabalho com GPU para medir fila, validação e latência ponta a ponta do backend real.
  Se a sessão não comportar a coleta completa, registrar a lacuna como limitação.
- **Refatoração e publicação:** priorizar refatoração, README e publicação do projeto.
  A curadoria do MVP tem teto de três entradas de replay aprovadas. Os três exemplos
  históricos já cobrem o roteiro da demo, incluindo a falha conhecida.
- **Space:** manter adiado e reavaliar quando houver tempo e catálogo elegível.

[Resultados e limitações](../reports/final-results-v1/RESULTADOS.md) ·
[Notas da versão](releases/v0.1-rag-mvp.md) · [Decisões](decisions.md)
