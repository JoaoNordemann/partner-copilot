# Dataset conversacional ABSA v1

Modelo base escolhido para o primeiro QLoRA: **Qwen2.5-1.5B-Instruct**. A ficha
oficial declara 1,54 bilhão de parâmetros, suporte a português e licença Apache
2.0. O tokenizer usa a mesma [revisão fixada do modelo](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/tree/989aa7980e4cf806f80c7fef2b1adb7bc71aa306).

## Formato e alocação

[Train JSONL](../data/absa/train-v1.jsonl) contém 1.263 exemplos. A
[validação](../data/absa/validation-v1.jsonl) tem 140. A primeira rodada usa os
1.263 IDs elegíveis do treino, dentro do teto de 1.500, com a reserva de templates
já aplicada. O ID fica em metadados. Cada `messages` contém uma mensagem `user`
com instrução curta e texto da review e uma mensagem `assistant` com JSON alvo.

O JSON alvo usa somente `aspects` na raiz. As chaves seguem a ordem `sabor`,
`tempo_entrega`, `temperatura`, `embalagem`, `preco`, `atendimento`, com valores
`pos` ou `neg` e sem espaços de formatação. Aspectos ausentes ficam sem chave.
Exemplo de alvo com sabor positivo e embalagem negativa.

```json
{"aspects":{"sabor":"pos","embalagem":"neg"}}
```

O formato para um alvo vazio é `{"aspects":{}}`. Treino e validação desta
versão têm zero exemplos vazios. O pipeline deve usar `apply_chat_template` do
tokenizer fixado para renderizar `messages`. Os arquivos preservam as mensagens
estruturadas e o perfil mede a sequência real, com marcadores e tokens do chat.

## Distribuição

| Aspecto | Treino pos | Treino neg | Validação pos | Validação neg |
| --- | ---: | ---: | ---: | ---: |
| `sabor` | 727 | 187 | 85 | 19 |
| `tempo_entrega` | 463 | 191 | 50 | 15 |
| `temperatura` | 336 | 124 | 48 | 14 |
| `embalagem` | 285 | 125 | 32 | 13 |
| `preco` | 189 | 48 | 23 | 6 |
| `atendimento` | 159 | 32 | 13 | 5 |

| Reviews | Treino | Validação |
| --- | ---: | ---: |
| 1 aspecto | 319 | 32 |
| 2 aspectos | 449 | 54 |
| 3 ou mais aspectos | 495 | 54 |
| Polaridades mistas | 447 | 48 |

Atendimento negativo e preço negativo têm os menores suportes. Na validação,
há cinco e seis ocorrências, respectivamente. Erros nesses pares podem alterar
bastante o F1 por classe, com efeito no macro-F1. Reportar suporte junto ao F1.

## Comprimento em tokens

Sequência completa com instrução, review, resposta e template oficial. Medida
sem truncar, usando Transformers 5.22.1 e o tokenizer na revisão fixada.

| Split | Mínimo | Mediana | p95 | Máximo | Tokens totais |
| --- | ---: | ---: | ---: | ---: | ---: |
| Treino | 104 | 135 | 170 | 219 | 172.956 |
| Validação | 103 | 135 | 174 | 200 | 19.296 |

Um limite inicial de **256 tokens** acomoda todos os exemplos desta versão.
Os totais excluem padding. O tempo e o pico de VRAM ainda dependem do batch,
da configuração QLoRA e da sessão T4.

## Reprodução

```powershell
python scripts/build_absa_dataset.py
python scripts/build_absa_dataset.py --check --local-files-only
```

A primeira execução baixa o tokenizer. O [relatório JSON](../data/absa/dataset-v1.json)
registra revisão, versão da biblioteca, hash do template, hash dos splits e dos
arquivos, contagens e perfil de tokens. Os conjuntos de teste ficam reservados
para avaliação após a escolha do checkpoint.
