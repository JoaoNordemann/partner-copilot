# Model card do PartnerCopilot ABSA · rascunho

O adapter LoRA do checkpoint 253 extrai seis aspectos de uma review em
português e atribui polaridade positiva ou negativa a cada aspecto mencionado.
A saída usa um único objeto JSON com a chave `aspects`. O uso avaliado é
análise de reviews sintéticas de entrega de comida.

A base é Qwen2.5-1.5B-Instruct na revisão
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, sob Apache 2.0.
[Licença na revisão do modelo base](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/blob/989aa7980e4cf806f80c7fef2b1adb7bc71aa306/LICENSE)

O ajuste usou 1.263 reviews sintéticas e 140 reviews sintéticas de validação,
sem dados do iFood. O checkpoint foi escolhido pela menor perda de validação
entre os três avaliados. O treinamento usou Transformers 5.20.2, TRL 1.17.1,
PEFT 0.21.2, bitsandbytes 0.50.2 e PyTorch 2.11.0+cu130, em Tesla T4 com
quantização NF4. [Treino e configuração](../reports/absa-qlora-train-v1/README.md)

| Conjunto sintético | Reviews | Macro-F1 |
| --- | ---: | ---: |
| Gold com referência humana | 100 | 0,9819 |
| Templates reservados | 346 | 0,9948 |
| Só famílias reservadas | 36 | 1,0000 em 9 pares com suporte |

A validação teve 140/140 JSONs válidos. A validação e o gold compartilham
84,1% e 70,4% das ocorrências de frases, respectivamente, com o treino.
No gold, os rótulos do gerador coincidiram com a referência humana em
87/100 reviews (macro-F1 0,9855). O QLoRA reproduziu as 13 divergências
de convenção do gerador e confundiu demora no atendimento com atraso na
entrega em duas outras reviews. O diagnóstico externo em texto real de
comércio eletrônico tem referência humana congelada e aguarda execução. [Resultados e auditoria](../reports/absa-eval-checkpoint-253-v1/README.md) ·
[Protocolo externo](absa-external-evaluation.md)

O manifesto fixa a revisão da base, a configuração de geração e os hashes
do adapter e do tokenizador. [Manifesto](../configs/absa-eval-v1.json)
