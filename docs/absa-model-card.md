# Model card do PartnerCopilot ABSA

O adapter está disponível no Hugging Face na revisão `742d1dcb93d71aee84fda6a84f5ca23dd8c281d6`.
[Revisão publicada](https://huggingface.co/jnordemann/partnercopilot-absa-qlora-v1/tree/742d1dcb93d71aee84fda6a84f5ca23dd8c281d6)

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
entrega em duas outras reviews.

Na B2W-Reviews01, de comércio eletrônico real em português brasileiro, o
adapter produziu 172/200 JSONs válidos. Nos 30 textos anotados por uma
pessoa, acertou todos os pares em 9/30 reviews, recuperou 9 dos 12 pares
anotados e acrescentou 20. Dez das 19 reviews com rótulo vazio receberam
um par extra. O TF-IDF acertou 18/30 por conjunto exato, recuperou 5 pares
e acrescentou 8. A validade de formato e os falsos positivos em
referências vazias excederam os limites do protocolo. O adapter é um
artefato de pesquisa sobre supervisão sintética. Os resultados de
transferência são específicos ao pequeno recorte B2W. A B2W foi usada
apenas na avaliação externa. [Fonte e licença B2W](https://github.com/americanas-tech/b2w-reviews01/blob/4639429ec698d7821fc99a0bc665fa213d9fcd5a/README.md#licensing)

[Resultados e auditoria](../reports/absa-eval-checkpoint-253-v1/README.md) ·
[Protocolo externo](absa-external-evaluation.md)

O manifesto fixa a revisão da base, a configuração de geração e os hashes
do adapter e do tokenizador. [Manifesto](../configs/absa-eval-v1.json)
