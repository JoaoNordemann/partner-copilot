# Demo Gradio local

A interface consulta a API HTTP; não carrega encoder, Chroma ou Mistral. Exibe
restaurante, pergunta, período, aspecto negativo, item e k. Os menus vêm da API.
Cada afirmação aparece ao lado de suas **reviews completas**, não apenas do trecho
escolhido pelo modelo. O caso n12 mostra por que isso importa: o elogio ao custo
não elimina a crítica de sabor na mesma fonte.

## Executar

O [caminho rápido do README](../README.md) usa `scripts/run_mvp.py` e monta a
interface em `/demo` na mesma API. O fluxo abaixo mantém os processos separados.

No repositório, instalar o extra (foi testado com Gradio 6.31.0):

```powershell
python -m pip install -e ".[demo]"
```

Terminal da API, usando um índice RAG já preparado:

```powershell
$env:LLM_BACKEND="fake"
$env:CHROMA_PATH="work/container-bootstrap-smoke/chroma"
$env:API_EMBEDDING_CACHE="work/hf-cache/sentence-transformers"
python -m uvicorn partner_copilot.api:app --host 127.0.0.1 --port 8000 --workers 1
```

Esses caminhos são locais desta máquina e não acompanham um clone. Para outro
ambiente, preparar o RAG com ingest.py ou com o [bootstrap Docker](docker.md).
Fake padrão devolve uma abstenção fixa e rotulada; não demonstra geração correta.
Também é possível apontar para a API do container CPU na mesma porta.

Em outro terminal:

```powershell
$env:DEMO_API_URL="http://127.0.0.1:8000"
python -m partner_copilot.demo
```

Abrir [a interface local](http://127.0.0.1:7860). DEMO_EXAMPLES_PATH altera o arquivo
de exemplos; GRADIO_SERVER_NAME/GRADIO_SERVER_PORT alteram bind/porta. O padrão é
loopback e `share=False`; analytics desabilitado. Não há publicação automática.
Sem API disponível, a aba histórica continua utilizável e o estado é explícito.

## O que a interface promete

- Sempre identifica dados sintéticos e a versão do prompt/parser na resposta.
- Fake é SIMULAÇÃO; replay é RESPOSTA GRAVADA. Nunca chamar replay de inferência ao vivo.
- Abstenção destacada; erros de contrato ficam como erros, sem saída bruta inválida.
- JSON completo em área expansível: estrutura v3, fontes, reviews e tempos por etapa.
- O campo `source_reviews` da API contém as fontes completas citadas. Com chunks,
  o original é carregado uma vez do split RAG validado. Se faltar a fonte completa,
  não é apresentado um chunk como se fosse a review inteira.
- O trecho também é conferido no original completo. Isso continua sendo uma
  verificação literal, não uma prova de sustentação ou pertinência.

## Três registros para a apresentação

A aba histórica é independente da API e vem de `configs/demo-examples.json`.
Não altera o catálogo de replay nem cria novas aprovações.

| Caso | Origem | O que mostrar | Limite |
| --- | --- | --- | --- |
| Sucesso n17 | v3 | Atendimento prestativo confirmado pela review completa | Parser v3 e sustentação na leitura de IA |
| Abstenção n20 | v3 | Não há marca de forno nas reviews do contexto | Resultado histórico; revisão de IA, sem avaliação nova |
| Falha n12 | v3 | Resposta aceita diz sabor bom, mas a fonte descreve gosto ruim no final | Falha confirmada pelo autor, em leitura própria. O parser aceitou a resposta apesar da contradição |

Saída bruta, pergunta, versão e proveniência ficam visíveis. SHA256 do arquivo de
origem e corpus acompanham o exemplo. Os registros não são chamados de limpos:
foram examinados e selecionados para esta demo, sem nova medição de qualidade.
Reproduzir sem modelos nem GPU:

```powershell
python scripts/build_demo_examples.py --check
python scripts/build_demo_examples.py
```

O segundo comando apenas reextrai os mesmos registros, sem gerar respostas.
Não consulta nem expõe o conjunto reservado para a avaliação final.

## Space e GPU

Space adiado: publicação não bloqueia a entrega local. Ainda não há catálogo
aprovado de replay v3; não contornar sua validação para publicar. O replay atual
usa contexto arquivado, sem busca ao vivo. Uma eventual busca CPU ao vivo deve
aparecer como painel separado, sem atribuir seu contexto à resposta gravada.
Não há Space criado, link público, nova tag ou inferência GPU nesta entrega.

Para uma apresentação real em Kaggle/Colab, manter a API/modelo uma vez na sessão
e apontar o cliente Gradio à API local. Se precisar de link temporário privado:

```python
import os
from partner_copilot.demo import build_demo

app = build_demo()
app.launch(share=True, auth=(os.environ["DEMO_USER"], os.environ["DEMO_PASSWORD"]))
```

Definir DEMO_USER/DEMO_PASSWORD nos segredos da sessão, sem imprimi-los ou gravá-los
no notebook. O link é um túnel temporário, protegido pelo login; encerrar a sessão
após a entrevista. Isso é uma instrução opcional, não um teste GPU realizado.
Referência de [launch e autenticação](https://www.gradio.app/docs/gradio/blocks).

## Verificação realizada

Testes sem GPU cobrem filtros, erros, rótulos, escape de HTML, texto completo e
regeneração dos exemplos. Smoke HTTP real com Gradio 6.31.0 no Windows conectou
à API fake com índice/encoder CPU em cache: menus, abstenção e três callbacks
históricos passaram. Inspeção no navegador confirmou n12 com afirmação e review
inteira lado a lado. Nenhuma chamada ao LLM ou ajuste de prompt foi feito.
