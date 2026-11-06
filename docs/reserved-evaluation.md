# Conjunto reservado para avaliação final

Status: dez perguntas n21–n30, sete respondíveis e três negativas, preparadas sem
qualquer inferência ou execução de retrieval. O número de chamadas de geração
limpas já medidas continua sendo nove; um conjunto reservado não aumenta esse n.

Arquivos em data/eval/reserved-final-v1/: questions.jsonl, label-audit.jsonl e
manifest.json. Não listar as perguntas nos relatórios, não usá-las em prompts,
exemplos, treinamento, calibração de score, escolha de k ou testes semânticos.
O fechamento é procedural, com hashes e Git, não criptografia ou acesso restrito.

## O que está congelado

O manifesto preserva a identidade do prompt partner-copilot-v3, parser-v3,
configuração explícita e hashes do núcleo de geração/retrieval no commit de origem.
Mantém retrieval_k=8, context_k=8, min_score=0.25, temperatura zero, seed 42,
max_new_tokens=512, margem=256 e pesos Mistral NF4. Rótulos vêm da leitura textual
pela IA, sem usar aspectos do gerador; a auditoria guarda fontes e escopo.

As perguntas foram criadas depois de conhecer resultados históricos. São novas
para uma futura execução congelada, mas usam o mesmo corpus de 100 reviews
conhecidas e padrões relacionados às avaliações anteriores. Não são holdout de
documentos, autoria cega ou gold humano independente. A ausência de duplicata
literal não garante ausência de paráfrase nem dificuldade equivalente.

## Verificar sem abrir a avaliação

```powershell
python scripts/check_reserved_eval.py
python scripts/check_reserved_eval.py --verify-runtime
```

O primeiro comando confere hashes, composição, labels/escopo, duplicatas literais
e o código no commit registrado. O segundo também exige que os arquivos atuais do
núcleo coincidam. Ambos exibem só contagens/estado; não carregam embeddings/LLM,
não executam consultas nem exibem perguntas. Exigem histórico Git disponível.
Não são execução de avaliação nem geram números de qualidade.

## Abrir uma única vez, somente quando for realizar a avaliação final

1. Registrar a abertura em um artefato separado, preservando o manifesto original.
2. Integrar a seleção do conjunto ao runner antes de abri-lo: o loader atual de
   final_v3 aceita apenas n11–n20. Adaptar entrada/ledger, sem mudar prompt, parser
   ou comportamento congelado. Validar o código com fixtures inventadas.
3. Conferir hashes, configuração e ambiente explícito; resolver e fixar a revisão
   dos pesos antes da primeira chamada. A revisão do Mistral não foi registrada
   nas rodadas anteriores; não fingir uma identidade que os artefatos não têm.
4. Executar no máximo uma inferência por pergunta, sem correção/retry. Registrar
   início durável antes da chamada e resultado a cada pergunta. Se uma chamada
   iniciou e seu resultado não foi salvo, marcar indeterminada e não repeti-la
   automaticamente. Preservar erros; não tratar falha de runtime como abstenção.
5. Salvar em reports/reserved-final-v1/ (a criar somente na execução), com hashes,
   versões, hardware, contexto, saída bruta, validação, tokens, latência e VRAM.
6. Reportar as dez perguntas, as chamadas reais e os erros/indeterminadas. Separar
   abstenções nas três negativas (com/sem LLM) das recusas indevidas nas sete
   respondíveis. Usar a mesma rubrica de sustentação e pertinência separadas.
7. Depois de ver as respostas, não ajustar configuração, prompt, parser, limiar,
   perguntas ou rótulos, nem executar nova rodada. Se descobrir problema de rótulo,
   registrar errata e limitação, preservando os originais e sem nova inferência.

Schema, aceitação, IDs e trechos literais continuam métricas distintas de fidelidade.
O manifesto registra os denominadores antes da execução. Usar a revisão humana
para conteúdo; a leitura da IA não preenche automaticamente esse julgamento.

Até a abertura, resultados deste conjunto permanecem **não medidos**. Se não houver
tempo ou GPU para executá-lo, manter a limitação de nove chamadas limpas já medidas
e registrar a execução reservada como trabalho futuro. Não executar agora nem
reabrir a escolha da versão em função destes exemplos.
