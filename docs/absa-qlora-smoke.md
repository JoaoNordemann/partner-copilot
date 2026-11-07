# Smoke de QLoRA ABSA no Kaggle

Importe [o notebook](../notebooks/absa-qlora-smoke.ipynb) em uma sessão nova.
Em Settings, escolha GPU T4 e habilite Internet. Confira o saldo semanal de GPU
no editor ou em Session management, informe o saldo em horas na primeira célula
e rode as células em ordem. O smoke exige saldo de pelo menos meia hora. O worker
para após 25 minutos, com até cinco segundos para encerramento forçado. O limite
inclui instalação, download, treino e recarga. Após salvar os artefatos, encerre a
sessão no Kaggle para liberar a GPU.

## Pilha e licença

A execução anterior de geração registrou torch 2.11.0+cu130, CUDA 13.0,
Transformers 5.20.2, bitsandbytes 0.50.2 e Accelerate 1.15.0 em Tesla T4.
O smoke registra as versões reais antes e depois de instalar TRL 1.17.1,
PEFT 0.21.2 e Datasets 5.1.0. Restrições de instalação preservam os quatro
pacotes presentes no runtime. Se bitsandbytes estiver ausente, instalar `0.50.2`.
Se a sessão diferir da família esperada, registrar o ambiente e parar no preflight. A documentação de bitsandbytes lista CUDA
13 e `sm75` no wheel Linux. [Guia da versão 0.50.2](https://huggingface.co/docs/bitsandbytes/v0.50.2/en/installation)

O código das wheels fixadas confirma `SFTConfig.max_length`,
`SFTConfig.completion_only_loss`, `SFTTrainer.processing_class` e
`prepare_model_for_kbit_training`. O notebook também confere as assinaturas
instaladas antes do download do modelo. A entrada para TRL é conversacional
`prompt`/`completion`. O template do tokenizer original renderiza os papéis e
o collator mascara o prompt. [SFT Trainer](https://huggingface.co/docs/trl/en/sft_trainer)

Base Qwen2.5-1.5B-Instruct, 1,54B parâmetros e suporte declarado a português.
A revisão `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` é pública, sem gating,
e declara Apache 2.0. [Ficha do modelo](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/tree/989aa7980e4cf806f80c7fef2b1adb7bc71aa306)

## Critérios de sucesso

- Verificar o hash do dataset versionado e selecionar 100 IDs de treino por hash
  com seed 2718. Executar 20 passos de otimizador com batch 1 e acumulação 5.
- Verificar camadas `Linear4bit` NF4 e parâmetros treináveis restritos a LoRA.
- Confirmar que os 100 prompts são prefixos da conversa tokenizada e têm rótulos
  `-100`. A parte supervisionada deve decodificar para o JSON esperado. Salvar
  os IDs dos tokens e rótulos do primeiro exemplo em `mask-example.json`.
- Medir perda antes e depois nos mesmos três exemplos de treino. A perda deve
  cair e permanecer finita. É um teste de funcionamento da pilha.
- Salvar adapter e tokenizer. Recarregar o adapter numa base nova com a mesma
  revisão e quantização. A perda após recarga deve reproduzir a anterior dentro
  de 1% relativo ou 0,01 absoluto.
- Medir picos de memória alocada e reservada pelo PyTorch até o fim do treino.
  Exigir 2 GiB de folga estimada entre memória livre no início e pico reservado.
  Registrar a duração dos passos sincronizados e a mediana dos passos 3 a 20.

`smoke.json` guarda ambiente, estado, perda, VRAM, tempos, resultado da recarga e
estimativa por época. Em falha, guarda estágio, tipo, mensagem e traceback.
`smoke.log` guarda o log integral, inclusive instalação e diagnóstico de limite.
Em erro de API, usar o erro e as versões registradas para escolher um conjunto
fixado e verificável antes do treino completo. Repetir somente após corrigir a
causa e conferir o saldo semanal.

## Planejamento da cota

Consultar o saldo da conta no [Kaggle](https://www.kaggle.com/docs/efficient-gpu-usage).
Usar no máximo 25 min neste smoke. Com o mesmo batch efetivo, uma época com
1.263 exemplos tem 253 passos. Multiplicar 253 pela mediana medida e somar a
carga, a validação, a gravação de checkpoints e a margem para a avaliação final.
Registrar o saldo após a sessão antes de marcar o treino completo.


## Pré-checagem local em CPU

Imports e collator verificados em Windows, Python 3.14.7, torch 2.15.0,
Transformers 5.20.2, bitsandbytes 0.50.2, Accelerate 1.15.0, TRL 1.17.1,
PEFT 0.21.2 e Datasets 5.1.0. O Qwen de teste foi criado com configuração
mínima e pesos aleatórios para exercitar a API em CPU. O tokenizer oficial
foi aplicado aos mesmos 100 exemplos do notebook. Em todos, o prompt recebeu
`-100` e a parte supervisionada decodificou para o JSON esperado.

`Dataset.from_list` falhou na serialização do fingerprint com dill 0.4.1
em PyArrow 26.0.1 e 24.0.0. Erro exato:
`_pickle.PicklingError: Can't pickle <class 'MonthDayNano'>: it's not found as builtins.MonthDayNano`.
`Dataset.from_generator` com cache Arrow em disco passou na mesma pilha com
PyArrow 26.0.1. O notebook usa essa opção antes de carregar os pesos.

## Resultado na T4

A sessão Kaggle passou com torch 2.11.0+cu130, CUDA 13.0, Transformers 5.20.2,
bitsandbytes 0.50.2, Accelerate 1.15.0, TRL 1.17.1, PEFT 0.21.2 e Datasets 5.1.0.
Os resultados, erros originais e configuração estão no [relatório do smoke](../reports/absa-qlora-smoke-v1/README.md).

TRL 1.17.1 converteu os adapters para BF16 no construtor do `SFTTrainer`. Na T4,
a correção foi restaurar os pesos treináveis LoRA para FP32 antes de criar o
optimizador. A base permaneceu NF4 e o compute FP16. Verificar os dtypes e a
máscara ao portar a configuração para o treino completo.
