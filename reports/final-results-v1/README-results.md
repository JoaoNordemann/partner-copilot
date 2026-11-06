## Resultados e limitações

A hipótese primária de retrieval não se confirmou: sem filtros, recall limitado@5
foi 0,2514 no MiniLM multilíngue contra 0,2583 no inglês,
com 4 vitórias, 16 empates e 4 derrotas nas
24 respondíveis. O multilíngue teve MRR maior, mas não venceu
palavras-chave em toda métrica. Filtrar restaurante fornece escopo e melhora o
resultado; isso, sozinho, não demonstra melhor entendimento semântico.

C e D aceitaram 2/27 saídas; D acrescentou
25 chamadas e recuperou
0 rejeições. O retry foi descartado.
Na v3 com perguntas então novas, 9/9 primeiros objetos
passaram o schema (todos com sufixo) e 6/9 passaram o
parser, incluindo duas abstenções do modelo. Havia evidência nas sete respondíveis,
mas apenas 3/4 respostas substantivas aceitas eram sustentadas
e pertinentes na leitura de IA. n12 passou ID/trecho e falhou no conteúdo; n14 teve
núcleo factual apoiado, mas foi bloqueada por transcrição. Geração fiel é o gargalo
observado, com custo adicional da validação estrita.

João leu 10 casos selecionados com auxílio no enquadramento:
3 sustentados, 2 parciais e 5 sem suporte. A revisão é
assistida, não cega, e não estima acurácia global nem valida um juiz LLM independente.
As 30 originais e n01–n10 são expostas; n11–n20 só eram limpas quanto a ajuste prévio
na execução congelada, com corpus conhecido e rótulos de IA. São resultados
descritivos de amostras pequenas, sem significância ou generalização demonstrada;
as mudanças conjuntas não isolam causalmente o efeito do JSON.

No Kaggle/Tesla T4 com NF4, a v1 teve mediana de geração de
8,80 s, carga de
87,84 s e pico alocado de
5,56 GB. Esses tempos não pertencem ao PC local;
carga não se soma por pergunta e reservado difere de alocado. As latências isoladas
de CPU não integram este snapshot histórico; foram medidas depois no
[relatório da API](../api-cpu-latency-v1/README.md), com hardware próprio.
Pesos integrais FP16 e custo monetário seguem pendentes. Nenhuma nova inferência
foi feita para gerar estas tabelas.

[Tabelas, contagens e proveniência](RESULTADOS.md).
