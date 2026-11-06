# Medições pendentes e momento de execução

Estas pendências não impedem reproduzir as tabelas existentes. Não foram realizadas
novas inferências, consultas de retrieval ou benchmarks nesta revisão documental.

## Na integração da API: uma medição de CPU

Medir uma única vez, com o código da API integrado, a latência isolada do embedding
de consulta e a latência da busca vetorial. Registrar separadamente o retrieval
total, declarando se inclui embedding, filtros e reconstrução dos documentos.

Antes da execução, fixar corpus/índice, perguntas e filtros, modelo/revisão, batching,
quantidade de repetições e warm-up. Identificar processador, RAM, threads, sistema,
versões, commit e estado de cache; separar carga do modelo de execução. Usar as
repetições definidas para produzir mediana e percentis, sem repetir o experimento
para selecionar o melhor resultado. Não usar as perguntas reservadas nesta medição.

Não inferir esses tempos pela diferença entre pipeline e geração. Os tempos totais
das ablações CPU existentes incluem carga/cache/download/indexação e não suprem a
medição isolada. Se não executado, manter a lacuna explícita.

## Na comparação de precisão: pesos FP16 em T4 de 16 GB

Comparação NF4 versus pesos integrais FP16 continua pendente para a etapa de
benchmark dedicada. GPU e capacidade explícitas; verificar folga de memória antes,
sem presumir que uma T4 de 16 GB comportará pesos, ativações e cache no orçamento.
Manter perguntas, prompt, parser e orçamento iguais; registrar OOM como resultado,
sem trocar silenciosamente hardware ou offload. Compute FP16 em NF4 não é o baseline
de pesos FP16. Não executar esta comparação agora.

## Avaliação reservada

O conjunto reservado continua sem execução e não entra no benchmark de CPU, demos,
calibração ou comparação exploratória. Sua abertura segue o protocolo próprio de
uma única rodada, sem ajuste posterior: [reserva final](reserved-evaluation.md).
