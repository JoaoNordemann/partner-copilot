# Auditoria semantica das 24 respondiveis de D

Revisor: Codex. Origem: leitura qualitativa por IA.

Critério: negacao clara da informacao pedida com pelo menos um ID rotulado relevante no contexto real. Nao contar como recusa total qualquer ocorrencia de marcador em resposta que tambem responde.

- Recusas claras com evidencia: 8/24 (q09, q11, q12, q14, q16, q21, q22, q24).
- Negacoes parciais com evidencia: 2/24 (q07 e q19); reportar separadamente, nao como dez recusas completas.
- Taxa formal registrada: 1/24, apenas q13; ela nao mede todas as recusas semanticas porque erros de parser nao viram Answer.abstained.
- Fonte rotulada relevante no contexto: 22/24. Falham q01 (posicao 6) e q13 (limiar). Antes do corte para cinco: 23/24.
- Ressalva de rotulo: q24 fala em preco/porcao, mas a fonte explicita apenas preco injusto. Excluindo esse caso discutivel, sao 7/24 recusas claras conservadoras. Nao alterar retrospectivamente o gold sem uma auditoria versionada.

| Questao | Evidencia no contexto | Categoria | Observacao |
| --- | --- | --- | --- |
| q01 | False | no_context_evidence | Recusa sem fonte rotulada relevante no contexto; fonte ficou na posicao 6. |
| q02 | True | answer_with_spurious_marker_or_noise | Ha resposta ao tema; marcador ou negacao sobre aspectos nao perguntados nao e contado automaticamente como recusa total. |
| q03 | True | answer_with_spurious_marker_or_noise | Ha resposta ao tema; marcador ou negacao sobre aspectos nao perguntados nao e contado automaticamente como recusa total. |
| q04 | True | answer_with_spurious_marker_or_noise | Ha resposta ao tema; marcador ou negacao sobre aspectos nao perguntados nao e contado automaticamente como recusa total. |
| q05 | True | answer_or_justified_limitation | Ha resposta ao tema; marcador ou negacao sobre aspectos nao perguntados nao e contado automaticamente como recusa total. |
| q06 | True | answer_with_spurious_marker_or_noise | Ha resposta ao tema; marcador ou negacao sobre aspectos nao perguntados nao e contado automaticamente como recusa total. |
| q07 | True | partial_answer_with_evidence_denial | Responde com uma fonte, mas nega criticas explicitas de sabor em outras reviews presentes. |
| q08 | True | answer_or_justified_limitation | Responde a opiniao de preco injusto e limita a generalizacao. A pergunta por que nao recebe causa explicita na fonte; nao contar essa limitacao como recusa indevida clara. |
| q09 | True | clear_refusal | Nega atraso apesar de mais de uma hora esperando, alem do combinado. |
| q10 | True | answer_with_spurious_marker_or_noise | Ha resposta ao tema; marcador ou negacao sobre aspectos nao perguntados nao e contado automaticamente como recusa total. |
| q11 | True | clear_refusal | Nega espera apesar dos 112 minutos; tambem troca duas semanas por dois meses. |
| q12 | True | clear_refusal | Nega reclamacoes de prazo apesar de O prazo passou e o pedido nada de chegar. |
| q13 | False | no_context_evidence | Abstencao da pipeline com contexto vazio, nao recusa semantica gerada pelo LLM. |
| q14 | True | clear_refusal | Reformula a pergunta impondo temperatura/embalagem e recusa, embora as fontes critiquem sabor. Reproduzir o contexto depois nao e responder. |
| q15 | True | answer_with_spurious_marker_or_noise | Ha resposta ao tema; marcador ou negacao sobre aspectos nao perguntados nao e contado automaticamente como recusa total. |
| q16 | True | clear_refusal | Nega criticas de sabor apesar da review gosto ruim no final. |
| q17 | True | answer_with_spurious_marker_or_noise | Ha resposta ao tema; marcador ou negacao sobre aspectos nao perguntados nao e contado automaticamente como recusa total. |
| q18 | True | answer_with_spurious_marker_or_noise | Ha resposta ao tema; marcador ou negacao sobre aspectos nao perguntados nao e contado automaticamente como recusa total. |
| q19 | True | partial_answer_with_evidence_denial | Responde parcialmente, depois nega outros casos apesar de outra fonte rotulada relevante no contexto. |
| q20 | True | answer_with_spurious_marker_or_noise | Ha resposta ao tema; marcador ou negacao sobre aspectos nao perguntados nao e contado automaticamente como recusa total. |
| q21 | True | clear_refusal | Nega recipiente desprotegido apesar da embalagem nao fechada direito. |
| q22 | True | clear_refusal | Nega insatisfacao de sabor apesar das criticas explicitas nas reviews. |
| q23 | True | off_topic_no_refusal | Resposta fora do assunto (embalagem), sem recusa explicita; nao contar como abstencao. |
| q24 | True | clear_refusal | Nega evidencia de custo/porcao; a fonte rotulada relevante critica preco. Ressalva: quantidade/porcao nao e explicitada na fonte; rotulo merece auditoria separada. |
