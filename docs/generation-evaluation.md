# Avaliação de geração no Colab

O notebook `notebooks/generation_eval.ipynb` instala o projeto com `pip install -e .`, monta o Drive e executa as 30 perguntas de `data/eval/human-v2/` com o corpus de avaliação isolado. O repositório é público: não precisa de token do GitHub para clonar.

## Preparação

1. Abra o notebook no Colab e selecione um runtime com GPU.
2. Adicione `HF_TOKEN` nos Secrets do Colab e permita acesso ao notebook. Use permissão de leitura. Nunca cole o token em uma célula.
3. Execute as células em ordem e autorize a montagem do Google Drive.

O token local fica apenas no `.env`, ignorado pelo Git. A instalação editável foi validada no PC. A consulta autenticada ao arquivo de configuração do modelo retornou HTTP 200; o modelo não apresentava bloqueio de aceite na API durante essa verificação. O token informado é fine-grained e seu acesso de leitura foi confirmado, mas também possui permissões de escrita. Antes de usar no notebook, restrinja as permissões no Hugging Face ou gere um token apenas de leitura; essa configuração de conta permanece pendente.

## Execução e retomada

A saída padrão do notebook é `/content/drive/MyDrive/PartnerCopilot/generation-v1.jsonl`. Cada pergunta produz uma linha com saída bruta, contexto, IDs, versão do prompt, latência e resultado ou erro. Cada linha é escrita com flush e fsync; um lock impede dois escritores locais simultâneos. Isso reduz perdas por interrupção, sem garantir a sincronização remota do Drive em caso de falha do serviço.

`--resume` pula tentativas já salvas e exige o mesmo experimento, configuração e ambiente registrados. Uma linha final interrompida é arquivada antes de ser recuperada. Corrupção no meio do arquivo impede retomada. Erros já registrados não são repetidos automaticamente: uma nova tentativa requer outro arquivo.

Comandos no diretório do projeto:

```bash
python scripts/evaluate_generation.py --output /caminho/resultados.jsonl --check-only
python scripts/evaluate_generation.py --output /caminho/resultados.jsonl --resume
python scripts/evaluate_generation.py --output /caminho/resultados.jsonl --summarize-only
```

O primeiro valida dados sem baixar pesos. O segundo exige CUDA e usa o Mistral real em NF4. O terceiro permite recalcular relatórios no PC, sem GPU. O notebook não atualiza o checkout automaticamente durante uma retomada.

## Relatório e leitura

O runner cria também `.summary.json` e `.review.md`. Taxas finais exigem 30 tentativas: abstenção nas 6 negativas, destaque para q25–q28, abstenção indevida nas 24 respondíveis e validade dos IDs citados no contexto. Erros são contados separadamente. Uma citação existente não comprova apoio factual.

A revisão manual fica pendente para q01, q09, q13, q22 e q25–q30, incluindo todas as negativas. Leia as dez saídas e registre evidência, recusa indevida e afirmações sem apoio. O checklist não significa revisão concluída.

O PC de preparação não tem CUDA: testes com doubles validam o mecanismo, mas não representam resultados ou desempenho do Mistral. A rodada real e a revisão das respostas devem ocorrer depois da execução no Colab.
