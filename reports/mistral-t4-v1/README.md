# Mistral na T4 em FP16, NF4 e HTTP real

A versão privada 368621275 do Kaggle terminou em 34 min 50 s. A cota
observada antes da sessão era de 88 min, com teto de 35 min para a rodada.
Os processos receberam somente a GPU 0, uma Tesla T4 com 15.360 MiB
anunciados. Foram executados NF4, FP16 e API NF4 em processos separados.
Os registros preservam o commit do protocolo, a revisão do modelo,
o ambiente, as saídas brutas e os intervalos da geração.
[Ambiente e sessão](session.jsonl) · [Resumo reproduzível](summary.json)

## Geração isolada

Carregamento a partir do cache local, com tokenizer e sincronização CUDA,
levou 31,89 s em NF4 e 9,36 s em FP16. O tempo de rede ficou fora.
A ordem fixa NF4 → FP16 permite que a segunda carga se beneficie do
cache do sistema operacional. Foram feitas duas chamadas de aquecimento
por modo. As 36 chamadas medidas mantiveram prompt v3, contexto,
decodificação gulosa e orçamento de 512 tokens novos.

| Modo | Conjunto | n | Pico alocado / reservado (GiB) | Latência mediana / máxima (s) | Tokens/s mediana / máxima | Aceitas |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| NF4 | Originalmente limpo | 9 | 4,53 / 5,00 | 5,64 / 20,54 | 13,24 / 15,95 | 6/9 |
| FP16 | Originalmente limpo | 9 | 14,16 / 14,31 | 9,07 / 22,50 | 9,23 / 10,23 | 8/9 |
| NF4 | Contaminado | 27 | 4,68 / 6,31 | 15,72 / 38,50 | 13,49 / 16,06 | 13/27 |
| FP16 | Contaminado | 27 | 14,32 / 14,38 | 20,45 / 52,90 | 9,33 / 9,88 | 11/27 |

FP16 completou o protocolo com margem pequena. A menor leitura de VRAM
livre após uma geração foi de cerca de 49 MiB com o prompt v3. A cerca de
128 KiB de cache KV por token, 49 MiB equivalem a aproximadamente 392
tokens de margem teórica. Contextos mais longos podem esgotá-la. NF4 teve menor pico e
maior taxa de tokens por segundo nos dois conjuntos, contrariando a
hipótese de que sua taxa seria menor ou igual à de FP16. Tokens/s é a
medida principal de velocidade, pois a latência também depende do tamanho
da saída. Largura de banda é uma explicação plausível, sem medição direta.
A ordem fixa também deixa efeitos térmicos ou de cache sem controle.

No conjunto originalmente limpo, 8/9 saídas brutas mudaram. Duas
passaram de rejeitadas em NF4 a aceitas em FP16. Entre as seis aceitas
nos dois modos, três respostas estruturadas mudaram. No conjunto
contaminado, mudaram 27/27 saídas brutas, oito decisões de aceitação
(cinco a favor de NF4 e três de FP16) e três das oito respostas
estruturadas aceitas nos dois modos. Aceitação mede o contrato do
parser. A rodada não adjudicou correção factual.

### Comparação entre sessões NF4

Na rodada v3 original, as medianas foram 6,3 s (n = 9) e 12,9 s
(n = 27). Nesta rodada foram 5,64 s e 15,72 s, respectivamente.
São variações descritivas entre sessões, sem atribuição causal.

Nas 27 chamadas contaminadas, 13 textos brutos mudaram e apenas q19
mudou de decisão, de aceita para rejeitada por trecho não literal.
Em q19, a terceira fonte mudou de `rev_002335` para `rev_000797`,
com um trecho que não aparece integralmente nessa fonte. As duas
sessões usaram geração gulosa, seed 42, limite de 512 tokens e as mesmas
versões registradas de Torch, Transformers e bitsandbytes. A causa da
mudança de saída não foi isolada. A execução não foi idêntica byte a byte.

### Leitura de casos pareados

- **n14:** em NF4, o trecho citado escreve «velo» no lugar de «velho»
  e falha na checagem literal. FP16 cita o trecho exato, incluindo a
  informação de que o lacre estava inteiro, e a saída passa.
- **n12:** os dois modos passam no parser e usam o mesmo trecho sobre
  custo-benefício para afirmar que o sabor era bom. A review descreve
  gosto ruim no final. A diferença de redação preserva o erro factual.
- **q05:** NF4 passa com uma citação sobre a tampa solta. FP16 usa a
  chave `fontes:` no lugar de `fontes` e falha no contrato. Em q09,
  FP16 falha ao juntar trechos que não aparecem nessa sequência.

Esses casos são leituras selecionadas. As contagens medem aceitação e
mudança de saída em duas amostras pequenas, sem estimativa de vantagem
factual de um modo sobre o outro. [Saídas NF4](nf4.jsonl) · [Saídas FP16](fp16.jsonl)

## API ponta a ponta

**Com o contrato estrito, o backend real respondeu com HTTP 200 a 8 de
20 requisições.** A amostra sequencial usa q01–q12 e q14–q21, todas
respondíveis e já vistas. q22 e q23 foram aquecimento. q24 e q25 foram
o par simultâneo e ficaram fora do denominador, incluindo a pergunta
sem resposta q25. A geração isolada usou um corpus de 100 documentos.
Os conjuntos e os contextos diferem, portanto a diferença nas taxas não
isola o efeito do tamanho do índice.

O servidor local usou NF4 na T4 e MiniLM multilíngue e Chroma em CPU,
com 862 documentos do split RAG. A amostra sequencial incluiu 20
requisições medidas após duas de aquecimento, no conjunto contaminado.
Todas chegaram à geração. Oito retornaram HTTP 200 e doze retornaram
502 por contrato de saída, com sete erros de esquema, três de trecho
e dois de ID de fonte. Não houve timeout na amostra.

| Etapa | n | Mediana | Máximo |
| --- | ---: | ---: | ---: |
| HTTP, todas as requisições | 20 | 24,07 s | 39,62 s |
| HTTP 200 | 8 | 13,73 s | 31,62 s |
| Embedding | 20 | 33,86 ms | 39,07 ms |
| Busca | 20 | 6,67 ms | 7,29 ms |
| Fila | 20 | 0,026 ms | 0,033 ms |
| Geração sem fila | 20 | 24,03 s | 39,57 s |
| Validação com HTTP 200 | 8 | 0,673 ms | 0,735 ms |

A API atual inclui a fila no campo de geração. A tabela subtrai esse
tempo uma vez. As rejeições não trazem a duração de validação medida,
por isso a linha de validação cobre as oito requisições com HTTP 200.

### Diagnóstico das rejeições HTTP

| Motivo registrado | n | Perguntas |
| --- | ---: | --- |
| Esquema inválido | 7 | q03, q05, q06, q10, q11, q15, q19 |
| Trecho sem correspondência literal | 3 | q02, q12, q21 |
| ID de fonte inválido | 2 | q04, q08 |

Os intervalos do servidor dão mediana de geração de 13,69 s nos 8
sucessos e 24,39 s nas 12 rejeições. As medianas HTTP correspondentes
são 13,73 s e 24,44 s. O registro HTTP e os intervalos não preservam a
saída bruta, os tokens gerados ou o motivo de parada para essas chamadas.
Mesmo com o teto padrão da API de 400 tokens, a duração não permite
identificar truncamento. Também não permite distinguir preâmbulo,
marcador misturado, ausência de citação ou corrupção de ID dentro dos
motivos registrados. As saídas da geração isolada não substituem as
saídas HTTP.

Embedding e busca foram medidos na CPU da sessão Kaggle com 862
documentos. Os 13,7 ms e 4,1 ms do teste anterior são de um Ryzen 5
5600 com 100 documentos. São ambientes e índices distintos.

### Concorrência

No único par simultâneo, as duas requisições retornaram HTTP 200. q25
terminou em 5,80 s, com 0,03 ms de fila. q24 terminou em 12,13 s, com
5,71 s de fila e 6,33 s de geração sem fila. O segundo intervalo de
geração começou 6,5 ms após o fim do primeiro. Os intervalos registrados
mostram execução serial no slot de geração.

[Notebook privado da rodada](https://www.kaggle.com/code/jnordemann/partnercopilot-mistral-t4-benchmark?scriptVersionId=368621275) · [Registros HTTP](api.jsonl) · [Intervalos](api-generation-intervals.jsonl)

Reproduza o resumo com `python scripts/summarize_gpu_benchmark.py reports/mistral-t4-v1`.
