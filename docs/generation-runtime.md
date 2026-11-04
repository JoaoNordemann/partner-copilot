# Execução do módulo de geração

`Mistral4bit` mantém tokenizer e pesos no objeto. `get_llm()` acrescenta um provider
preguiçoso compartilhado por processo, com lock para impedir duas cargas concorrentes.
A pipeline pode ser construída com `RAGPipeline(retriever)` e só obtém o modelo após
recuperar documentos; retrieval vazio não carrega pesos. Uma configuração diferente
de modelo/geração após a primeira carga exige reiniciar o processo. Instanciar
`Mistral4bit` manualmente continua criando outro objeto: use o provider no serviço.
Cada worker/processo tem sua própria instância e ocupa memória própria.

## Dtype e geração

A quantização continua NF4 em 4 bits, com double quantization. O compute_dtype é
bfloat16 quando todas as GPUs visíveis suportam bf16 (consulta nativa quando a API
permite); caso contrário, float16. Essa política conservadora evita escolher bf16
para um shard incompatível no device_map automático. O modelo entra em eval().
O caminho real exige CUDA e falha antes de carregar pesos quando não há GPU.

O adaptador continua usando uma única mensagem user, apply_chat_template,
add_special_tokens=False e truncation=False. Temperatura zero desativa do_sample
e omite temperature/top_p dos argumentos; temperatura positiva ativa amostragem.
Apenas os IDs de tokens após o comprimento da entrada são decodificados. O número
de tokens gerados inclui tokens especiais, como EOS, mesmo que não apareçam no texto.

## Reprodutibilidade

Defaults: TEMPERATURE=0.0 e GENERATION_SEED=42. Ambos vêm de Settings/.env;
valores explícitos continuam tendo precedência. A seed é reiniciada em cada chamada,
não apenas ao iniciar o processo, para a ordem das perguntas não consumir sequências
aleatórias diferentes. fork_rng preserva e restaura o RNG da CPU e das GPUs usadas.
A seed da CPU é aplicada no gerador padrão e a seed CUDA só nas GPUs do modelo.

Um lock de inferência compartilhado serializa a manipulação do RNG e dos contadores
de memória. Isso reduz concorrência de geração neste processo; a latência total da
pipeline inclui espera por esse lock. O lock não transforma os contadores CUDA em
medição isolada de qualquer outro código do processo que use a mesma GPU.

Seed fixa, eval e greedy decoding reduzem variação, mas não garantem resultados
bit a bit entre hardware, versões de Torch/Transformers/bitsandbytes e kernels
diferentes. Registre esse ambiente junto com seed, temperatura, versão do prompt e
modelo em cada experimento. Mudanças de parâmetros não alteram silenciosamente o
prompt v1: seu hash e instruções permaneceram iguais.

## Tokens e margem de segurança

O número de tokens é medido depois do chat template e inclui todas as instruções,
metadados, reviews e marcadores do tokenizer. O limite efetivo é o menor entre a
janela informada pelo modelo e o limite positivo informado pelo tokenizer.
A chamada só prossegue quando:

```text
prompt_tokens + max_new_tokens + GENERATION_CONTEXT_MARGIN_TOKENS <= context_window_tokens
```

A margem padrão é 256 tokens adicionais à reserva de resposta. Não há truncamento
silencioso. Se a conta não fechar, GenerationContractError ocorre antes de generate.
CONTEXT_K=5 continua sendo um limite de documentos, não um orçamento de tokens.

## Medições retornadas e registradas

O contrato generate(prompt) -> str permanece disponível. Para obter o texto e as
medições da mesma chamada sem depender de um last_metrics compartilhado, use
`generate_with_metrics(prompt) -> GenerationResult`.

A pipeline reconhece explicitamente MeasuredLLM e inclui os dados em
`answer.metadata.generation`, inclusive se o modelo se abstiver com o marcador.
Um LLM falso ou simples que só implemente generate continua aceito, mas generation
fica null. Retrieval vazio também tem generation=null.

| Campo em metadata.generation | Interpretação |
| --- | --- |
| latency_ms | Tempo de template, tokenização, cópia, geração e decode; sem espera pelo lock e sem carga inicial. |
| model_load_latency_ms | Tempo da carga única do objeto, incluindo tokenizer e eval; é repetido como atributo, não custo novo de cada pergunta. |
| prompt_tokens / generated_tokens | Quantidades reais de tokens de entrada e continuação. |
| max_new_tokens / context_window_tokens / context_margin_tokens | Reserva, janela e folga usadas para validar a chamada. |
| seed / temperature / do_sample / compute_dtype | Parâmetros efetivos usados nessa geração. |
| vram_baseline_allocated_bytes | Memória alocada por GPU antes da chamada, com pesos residentes. |
| vram_peak_allocated_bytes | Pico de memória alocada por GPU durante a chamada. |
| vram_peak_reserved_bytes | Pico reservado pelo allocator por GPU, incluindo cache. |

As memórias usam bytes e chaves cuda:0, cuda:1 etc. Contadores são reiniciados a cada
chamada; sincronização CUDA antes/depois impede medir somente o despacho assíncrono.
O pico alocado é absoluto, inclui pesos residentes e não é apenas o incremento das
ativações. Compare com o baseline para estudar esse incremento. Memória reservada
não é igual a memória efetivamente usada, pois pode conter cache de chamadas anteriores.
O pico transitório de carregamento não é medido por esses contadores de inferência.

`metadata.latency_ms` continua medindo toda a pipeline. Na primeira chamada preguiçosa,
inclui a carga dos pesos; nas seguintes, não. O adaptador emite eventos INFO
llm_model_loaded e llm_generation_completed, sem registrar prompt, reviews ou token HF.

## Uso em uma aplicação com GPU

```python
from partner_copilot.pipeline import RAGPipeline

pipeline = RAGPipeline(retriever)  # Crie uma vez no ciclo de vida da aplicação.
answer = pipeline.ask(question, restaurant_id)
print(answer.model_dump_json(indent=2))
```

Ou, para medir somente geração de um prompt já montado:

```python
from partner_copilot.generation.provider import get_llm

llm = get_llm()
result = llm.generate_with_metrics(prompt)
print(result.text)
print(result.metrics.model_dump_json(indent=2))
```

O provider padrão devolve Mistral4bit, que implementa generate_with_metrics.
Configure logging com nível INFO na aplicação se quiser persistir os eventos;
os mesmos valores já são retornados no objeto da resposta.

## Validação e limites observados

Os testes usam tensores CPU, modelos falsos e contadores CUDA simulados. Verificam
seed por chamada, restauração de RNG, carregamento único sob concorrência, dtype,
eval, contagem/decode, margem, sincronização, medição por GPU e propagação à pipeline.
O grupo leve do CI inclui o provider e usa dependências sem frameworks de modelos.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_generation_provider.py tests/test_generation_llm.py tests/test_configuration_integration.py -v
```

Neste ambiente foi detectado Torch 2.15.0+cpu, CUDA indisponível. Portanto não existem
novos números reais de latência ou VRAM de Mistral-7B nesta etapa. A instrumentação
está testada com doubles e deverá ser medida na GPU de execução; não tratar valores
simulados dos testes como benchmark.
