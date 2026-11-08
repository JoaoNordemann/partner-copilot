# Treino ABSA com QLoRA v1

Treino concluído em 7 de novembro de 2026 no Kaggle, com acelerador T4 x2 e
`CUDA_VISIBLE_DEVICES=0`. Foram 3 épocas e 759 passos de otimizador, com 1.263
reviews de treino e 140 de validação. As 1.403 máscaras foram conferidas para
supervisionar apenas o JSON da resposta. A sessão foi encerrada após baixar e
verificar o pacote. [Notebook no Kaggle](https://www.kaggle.com/code/jnordemann/partnercopilot-absa-qlora-treino-v1/edit)

| Época | Passo | Perda de validação |
| ---: | ---: | ---: |
| 1 | 253 | 0,00038059 |
| 2 | 506 | 0,01182981 |
| 3 | 759 | 0,00976478 |

O adapter exportado é o `checkpoint-253`, escolhido pelo menor `eval_loss`.
Das 377 ocorrências de frases normalizadas na validação, 317 (84,1%) também
aparecem no treino.
A perda pode refletir memorização de templates. O gold humano e os templates
reservados ficaram fora da execução e aguardam a avaliação final com esse
checkpoint. [Protocolo e auditoria da validação](../../docs/decisions.md#absa-configuração-do-primeiro-treino-completo)

| Medida na Tesla T4 | Resultado |
| --- | ---: |
| Treino com validação e checkpoints | 41 min 18 s |
| Worker, incluindo preparação e exportação | 42 min 40 s |
| Sessão, do disparo ao encerramento | cerca de 46 min |
| Mediana por passo do otimizador | 3,19 s |
| Carregamento do modelo | 24,54 s |
| Pico de VRAM alocada | 1,94 GiB |
| Pico de VRAM reservada | 2,18 GiB |
| Cota semanal exibida antes e depois | 29 h 48 min / 29 h 02 min |

A base Qwen2.5-1.5B-Instruct usou NF4 com dupla quantização, compute FP16 e
9.232.384 parâmetros LoRA treináveis em FP32. Python 3.13.16, torch 2.11.0+cu130,
CUDA 13.0, Transformers 5.20.2, bitsandbytes 0.50.2, Accelerate 1.15.0,
TRL 1.17.1, PEFT 0.21.2 e Datasets 5.1.0.

- [Métricas, curva de treino e hashes dos splits](training.json)
- [Log do worker](training.log)
- [Configuração executada](config.json)
- [Restrições de dependências](constraints.txt)
- [Notebook reproduzível](../../notebooks/absa-qlora-train.ipynb)

Commit dos insumos `82880bcff61d9c32cd910460a05eee6ee78cd858`.
O pacote local `absa-qlora-train-2e80ef8b.zip` contém o adapter, o tokenizador e
os registros da execução.

- SHA-256 do adapter `ef97282c03432c22c9735f419463d1e936b0729ac099052ac96e7b170c7e1d05`
- SHA-256 do ZIP `d7b3a90910071bfd2d9333c8eb7180e68964d2d700ce1438c6fb9fa5898764be`
