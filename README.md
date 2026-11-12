# PartnerCopilot

[![CI](https://github.com/JoaoNordemann/partner-copilot/actions/workflows/retriever-unit.yml/badge.svg)](https://github.com/JoaoNordemann/partner-copilot/actions/workflows/retriever-unit.yml)

Encontrar evidências sobre atrasos, atendimento ou qualidade entre muitas avaliações dá trabalho a quem opera um restaurante. O PartnerCopilot busca evidências para perguntas como “Por que os pedidos estão chegando atrasados?”, cita as avaliações usadas e se abstém quando falta evidência. O protótipo usa dados sintéticos.

| Medição | Resultado |
| --- | --- |
| Busca por restaurante | A cobertura da evidência nos cinco primeiros resultados (recall limitado@5) subiu de **25,14% para 74,65%** ao restringir a busca ao restaurante (24 perguntas sintéticas já vistas). |
| Filtro por aspecto | A proporção de posições relevantes entre os cinco primeiros resultados (precision@5) subiu de **30,83% para 37,50%**, de um teto de 45,83% (24 perguntas sintéticas já vistas). |
| Contrato de geração | O JSON v3 passou no parser em **14/27** saídas, ante 2/27 em texto livre (perguntas antigas usadas em iterações). |
| Extração em e-commerce | Em avaliações de e-commerce, o modelo ajustado deixou a lista de aspectos vazia em **3/19** casos em que deveria, ante 17/19 das regras. |
| API real | Mediana de **24,07 s** ponta a ponta em NF4 na T4 (20 requisições com perguntas já vistas, incluindo 8 sucessos e 12 rejeições por saída fora do contrato). |

[Resultados e métodos](reports/final-results-v1/RESULTADOS.md) · [Filtro por aspecto](reports/absa-retrieval-v1/README.md) · [Avaliação externa](docs/absa-external-evaluation.md) · [Medição na T4](reports/mistral-t4-v1/README.md)

## Rodar em CPU

A demo em CPU simula uma abstenção fixa no modo padrão e mostra respostas gravadas na aba histórica. A geração ao vivo requer GPU.

Na raiz do clone, com Python 3.12 ou 3.13 e ambiente virtual ativo:

```powershell
python -m pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.2,<3"
python -m pip install -r requirements-cpu.txt "gradio>=6,<7" "httpx>=0.27,<1"
python scripts/run_mvp.py
```

Abra a [demo](http://127.0.0.1:8000/demo/) ou a [documentação da API](http://127.0.0.1:8000/docs).
O primeiro uso baixa o encoder e monta o índice. A aba histórica inclui as avaliações completas usadas como fonte.

## O que não funcionou

- O retry acrescentou 25 chamadas e recuperou **0/25** rejeições.
- Em `n12`, uma resposta aceita usou um elogio ao custo-benefício para afirmar que o sabor era bom. A review relatava gosto ruim no final.
- O QLoRA previu sabor ou temperatura em **87/200** textos de e-commerce. Seu treino sintético não incluía exemplos sem aspecto aplicável.

## Limitações e trabalho futuro

Os testes de busca usam corpus sintético e perguntas já vistas. O ganho do filtro por aspecto foi igual com rótulos QLoRA e do gerador. A avaliação externa é de e-commerce, e o desempenho em reviews reais de restaurantes segue em aberto. Uma próxima versão deve incluir exemplos sem aspecto aplicável, reservar um novo teste anotado antes do treino e comparar o resultado com regras simples.

## Demo local

A aba de casos históricos exibe respostas gravadas em dados sintéticos.
O GIF alterna os três casos da demo, com a falha identificada na interface.

![Três casos gravados da demo local do PartnerCopilot](docs/assets/demo/casos-gravados.gif)

[Sucesso](docs/assets/demo/n17-sucesso.jpg) ·
[Abstenção](docs/assets/demo/n20-abstencao.jpg) ·
[Falha](docs/assets/demo/n12-falha.jpg) ·
[Curadoria e decisão sobre o Space](docs/demo.md#curadoria-das-respostas-gravadas)

## Detalhes técnicos

<details>
<summary>Arquitetura, resultados adicionais e execução em Docker</summary>

FastAPI e Gradio usam um índice Chroma persistente. A ingestão valida e separa dados, divide textos longos e atualiza os documentos pelos mesmos IDs. Embeddings multilíngues e filtros recuperam o contexto. A geração v3 produz JSON e o parser confere esquema, IDs e trechos literais.

<!-- BEGIN GENERATED RESULTS -->
- RAG de reviews sintéticas, com citações verificadas e abstenção; sem dados reais do iFood.
- Retrieval: recall limitado@5 sem filtro de 0,2514 no multilíngue e 0,2583 no inglês; 4V/16E/4D em 24 perguntas respondíveis expostas.
- Geração v3: 6/9 saídas aceitas, incluindo duas abstenções; 3/4 substantivas aceitas sustentadas e pertinentes na leitura de IA.
- Retry descartado: 25 chamadas extras, 0 rejeições recuperadas; formato válido não garante resposta correta.
- Evidência limitada por corpus conhecido, amostras pequenas e revisão humana assistida.

[Resultados, tabelas e limitações](reports/final-results-v1/RESULTADOS.md).
<!-- END GENERATED RESULTS -->

Em T4 de 16 GB, o Mistral 7B em 4 bits usou **4,53 GiB de pico alocado** e respondeu em **5,64 s** (mediana, n = 9, conjunto originalmente limpo). Em FP16, coube com **14,16 GiB de pico alocado** e mediana de **9,07 s** no mesmo conjunto. [Comparação na T4](reports/mistral-t4-v1/README.md)

O container CPU com backend `fake` retornou HTTP 200 em `/health` e `/ask` em Ubuntu no GitHub Actions. O caminho GPU está **não testado em container**. [Docker](docs/docker.md)

As regras e partes do pipeline foram escritas com assistência de IA. O autor revisou os resultados.

</details>

[API](docs/api.md) · [Testes](docs/testing.md) · [Decisões](docs/decisions.md) · [Versão v0.2](docs/releases/v0.2-aspects.md) · [Status do estudo](docs/study-status.md) · [Notebook ABSA](https://www.kaggle.com/code/jnordemann/partnercopilot-absa-em-portugu-s?scriptVersionId=368237209)
