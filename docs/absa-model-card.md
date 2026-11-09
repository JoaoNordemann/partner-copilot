# Model card do PartnerCopilot ABSA

O checkpoint 253 é um adapter LoRA para estudar extração de aspectos
e polaridade em reviews de entrega de comida em português. O contrato
de saída é um objeto JSON com a chave `aspects`. Os seis aspectos são
`sabor`, `tempo_entrega`, `temperatura`, `embalagem`, `preco` e
`atendimento`. Cada par usa `pos` ou `neg`. Aspectos sem evidência
devem ser omitidos. O uso em textos reais de produção sem validação
no domínio de destino fica fora de escopo.

A base é **Qwen2.5-1.5B-Instruct** na revisão
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, sob **Apache 2.0**.
A versão publicada carrega o adapter separadamente sobre a base NF4.
[Licença oficial da base](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/blob/989aa7980e4cf806f80c7fef2b1adb7bc71aa306/LICENSE) ·
[Revisão original dos pesos do adapter](https://huggingface.co/jnordemann/partnercopilot-absa-qlora-v1/tree/742d1dcb93d71aee84fda6a84f5ca23dd8c281d6)

## Dados e treino

Os textos de treino e validação são 100% sintéticos, sem dados do iFood.
O gerador de reviews produziu 3.000 textos com seed 42, janela de 90 dias
e data de referência de 1 de novembro de 2026. A divisão ABSA usou seed
2718. São 1.263 reviews de treino, 140 de validação, 100 do gold sintético
com anotação humana e 346 no teste de templates reservados, dos quais 36
têm apenas famílias inéditas. A B2W contém texto real e foi usada somente
na avaliação externa. [Gerador](../scripts/generate_synthetic_data.py) ·
[Manifesto do dataset e sementes](../data/absa/dataset-v1.json) ·
[Divisão dos dados](absa-splits.md)

O treino com NF4, dupla quantização e cálculo FP16 usou uma Tesla T4
no Kaggle, com 3 épocas e 759 passos. Treino, validação e checkpoints
levaram **41 min 18 s**. O checkpoint 253, da primeira época, teve
a menor perda de validação entre os três avaliados. Versões do treino
**TRL 1.17.1, PEFT 0.21.2, Transformers 5.20.2, bitsandbytes 0.50.2
e PyTorch 2.11.0+cu130**, com CUDA 13.0.
[Relatório e configuração do treino](../reports/absa-qlora-train-v1/README.md)

## Resultados

Cada célula da tabela mostra **reviews com acerto exato / total** e o
macro-F1 dos pares com suporte. Acerto exato exige que todos os pares
coincidam com a referência. Os 36 exemplos inéditos são um recorte
dos 346 reservados. A B2W avalia quatro aspectos e tem cinco pares com
suporte, por isso o macro-F1 não é diretamente comparável ao dos
conjuntos sintéticos completos.

| Conjunto | QLoRA | Qwen few-shot | Regras | TF-IDF |
| --- | ---: | ---: | ---: | ---: |
| Gold sintético com anotação humana | 85/100 · 0,9819 | 5/100 · 0,5162 | 10/100 · 0,4156 | 60/100 · 0,8688 |
| Templates reservados | 340/346 · 0,9948 | 11/346 · 0,5524 | 26/346 · 0,3198 | 101/346 · 0,7240 |
| Só famílias inéditas | 36/36 · 1,0000 | 7/36 · 0,4719 | 16/36 · 0,3333 | 22/36 · 0,3980 |
| B2W com referência humana | 9/30 · 0,6758 | 0/30 · 0,3996 | 23/30 · 0,4100 | 18/30 · 0,2171 |

O QLoRA gerou JSON válido em 140/140 na validação, 100/100 no gold,
346/346 nos reservados e 172/200 no lote B2W. Nos 30 textos reais
anotados, o QLoRA recuperou 9 pares, acrescentou 20 e omitiu 3. O
Qwen few-shot recuperou 12, acrescentou 95 e omitiu zero. As regras
recuperaram 6, acrescentaram 2 e omitiram 6. O TF-IDF recuperou 5,
acrescentou 8 e omitiu 7. [Resultados sintéticos e auditoria](../reports/absa-eval-checkpoint-253-v1/README.md) ·
[Resultados externos e revisão humana](absa-external-evaluation.md)

## Limitações

O extrator segue a convenção de rótulos do gerador nos **13 de 100
textos do gold** em que ela diverge do guia humano. O gold compartilha
**70,4% das ocorrências de frases** com o treino. Em duas outras reviews,
o modelo confundiu demora para responder no atendimento com atraso na
entrega. Em `rev_002800`, classificou como sabor negativo um gosto
diferente do habitual, cuja polaridade ficou em aberto no guia humano.
Foi o único caso em que o TF-IDF venceu o QLoRA no gold pelo F1 por review.
[Auditoria das divergências](../reports/absa-eval-checkpoint-253-v1/README.md)

A avaliação externa tem 30 textos com referência de um único anotador e
usa um domínio diferente. Na B2W, 28/200 saídas do QLoRA foram inválidas
e 10/19 reviews com referência vazia receberam pelo menos um par extra.
A transferência para reviews reais de restaurantes exige avaliação
própria. [Protocolo e resultados B2W](absa-external-evaluation.md)

## Carregamento em GPU

Na sessão Kaggle, instalar `transformers==5.20.2`, `peft==0.21.2`
e `bitsandbytes==0.50.2` sobre o PyTorch com CUDA. O exemplo carrega
as revisões fixas sem autenticação e usa decodificação gulosa. O
tokenizador e o template de chat vêm do repositório do adapter.

```python
import torch
from huggingface_hub import snapshot_download
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

adapter = snapshot_download(
    "jnordemann/partnercopilot-absa-qlora-v1",
    revision="742d1dcb93d71aee84fda6a84f5ca23dd8c281d6",
    token=False,
)
tokenizer = AutoTokenizer.from_pretrained(adapter, local_files_only=True)
quant = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.float16,
)
base = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-1.5B-Instruct",
    revision="989aa7980e4cf806f80c7fef2b1adb7bc71aa306",
    quantization_config=quant,
    dtype=torch.float16,
    attn_implementation="sdpa",
    device_map={"": 0},
    token=False,
)
model = PeftModel.from_pretrained(base, adapter).eval()

review = "A entrega atrasou e a comida chegou fria."
instruction = (
    "Classifique os aspectos sabor, tempo_entrega, temperatura, embalagem, preco e atendimento. "
    "Use pos ou neg e omita aspectos sem opinião clara. "
    'Responda só com um objeto JSON com a chave "aspects".'
)
inputs = tokenizer.apply_chat_template(
    [{"role": "user", "content": instruction + "\n\nReview:\n" + review}],
    tokenize=True,
    add_generation_prompt=True,
    return_dict=True,
    return_tensors="pt",
).to("cuda:0")
with torch.inference_mode():
    ids = model.generate(
        **inputs, do_sample=False, max_new_tokens=96, use_cache=True
    )[0, inputs["input_ids"].shape[1]:].tolist()
eos = model.generation_config.eos_token_id
eos = {eos} if isinstance(eos, int) else set(eos or ())
end = next((i for i, token in enumerate(ids) if token in eos), len(ids))
print(tokenizer.decode(ids[:end], skip_special_tokens=False))
```

O teste no Kaggle retornou para a entrada do exemplo
`{"aspects":{"tempo_entrega":"neg","temperatura":"neg"}}`.
[Manifesto com revisões, configuração e hashes](../configs/absa-eval-v1.json)


O teste em uma sessão nova do Kaggle baixou a base e o adapter sem
autenticação, com cache vazio e sem dataset anexado. Em uma Tesla T4,
os três exemplos sintéticos retornaram JSON válido e todos os pares
esperados. Os exemplos cobriram prazo e temperatura, sabor e embalagem,
e atendimento e preço.
