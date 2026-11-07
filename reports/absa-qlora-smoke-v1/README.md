# Smoke ABSA QLoRA na Tesla T4

O smoke passou em uma sessão Kaggle configurada com T4 x2 e o worker limitado
à GPU 0. A sessão foi encerrada após baixar o pacote de evidências.
[Notebook Kaggle](https://www.kaggle.com/code/jnordemann/partnercopilot-absa-qlora-smoke/edit)

A base Qwen2.5-1.5B-Instruct foi carregada em NF4 com compute FP16 e 9.232.384
parâmetros LoRA treináveis em FP32. Python 3.13.16, torch 2.11.0+cu130,
Transformers 5.20.2, bitsandbytes 0.50.2, Accelerate 1.15.0, TRL 1.17.1,
PEFT 0.21.2 e Datasets 5.1.0. O modelo público declara Apache 2.0.
[Ficha da revisão](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/tree/989aa7980e4cf806f80c7fef2b1adb7bc71aa306)

| Medida | Resultado |
| --- | ---: |
| Exemplos de treino e máscaras verificadas | 100 |
| Passos de otimizador | 20 |
| Perda inicial nos três exemplos fixos | 1,18449 |
| Perda após o smoke e após recarregar | 0,04228 |
| Pico alocado | 2,109 GiB |
| Pico reservado | 2,227 GiB |
| Folga estimada na T4 | 12,233 GiB |
| Mediana dos passos 3 a 20 | 2,916 s |
| Duração do worker bem-sucedido, com cache | 86,39 s |
| Estimativa por época completa, 253 passos | 12,29 min |

No primeiro exemplo, 124 tokens do prompt receberam `-100`. Os 22 tokens
supervisionados reproduziram o JSON alvo ao decodificar. A perda foi medida nos
mesmos três exemplos da amostra de treino antes, depois e após a recarga do
adapter numa base nova. O resultado verifica a pilha. F1 e generalização serão
medidos no protocolo de avaliação separado.

## Diagnósticos durante a sessão

1. **Preflight, 7,91 s.** A imagem Kaggle veio sem bitsandbytes. A checagem inicial
   devolveu `RuntimeError: Runtime differs from the targeted T4 / torch 2.11 / CUDA 13 / Transformers 5 / BNB 0.50 stack.`
   A correção instalou `bitsandbytes==0.50.2` preservando torch, Transformers e Accelerate.
   [Relatório do preflight](preflight-missing-bnb.json)
2. **Primeiro passo, 79,52 s de worker.** O carregamento NF4 e as 100 máscaras
   passaram. O GradScaler falhou com
   `NotImplementedError: "_amp_foreach_non_finite_check_and_unscale_cuda" not implemented for 'BFloat16'`.
   TRL 1.17.1 converteu os pesos LoRA para BF16 no construtor. Restaurar os pesos
   treináveis para FP32 após o construtor permitiu executar os 20 passos.
   [Relatório do erro](retry-report.json)

## Artefatos e cota

- [Métricas, versões, amostra e tempos por passo](smoke.json)
- [Log do worker bem-sucedido](smoke.log)
- [IDs dos tokens e máscara do primeiro exemplo](mask-example.json)
- [Restrições do runtime](constraints.txt)

O adapter ficou no pacote local `absa-qlora-smoke-53a40201.zip`.
SHA-256 do adapter `5bfd903d8338f7302f5079dc5241c2d6e3ab6a1b91acf27f5ac74245e4601324`.
SHA-256 do ZIP `83fa52d405a12b12ae65ec1f2ae7be8f12e98f66042bf4a0cea139b507d1ca7e`.
A cota exibida antes de iniciar era 30 h de 30 h. A projeção de 12,29 min por
época usa o batch efetivo de cinco e exclui carga, validação e checkpoints.
Rever o saldo antes do treino completo e reservar tempo para a avaliação final.

Commit dos insumos da execução `1e25fbff62d9050391a2300eb82d5b6d3c5d932b`.
SHA-256 do worker `298b6d8a0d09e4094511b3ae3186925aad65c203da6afe2791bc31ef2d8dab61`.
