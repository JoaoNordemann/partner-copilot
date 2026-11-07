# Ficha do dataset ABSA v1

**Objetivo.** Extrair de uma review em português os aspectos mencionados e sua
polaridade `pos` ou `neg`. Os seis aspectos são `sabor`, `tempo_entrega`,
`temperatura`, `embalagem`, `preco` e `atendimento`. Aspectos sem polaridade
identificável ficam ausentes do JSON.

**Origem.** Corpus de 3.000 reviews sintéticas, gerado com seed 42 e janela de
90 dias até 2026-11-01. O treino usa rótulos do gerador. O corpus contém dados
sintéticos e nenhum dado real do iFood. [Commit que gerou o corpus](https://github.com/JoaoNordemann/partner-copilot/commit/d6aedfd3eff5acc58609ee75e04d8c46fa6a532e)

**Splits.** 1.263 reviews de [treino](train-v1.jsonl), 140 de [validação](validation-v1.jsonl),
346 no [teste de templates reservados](splits-v1.json) e 100 no
[gold humano](../gold/aspects_100.human.jsonl). [Manifesto com hashes e contagens](dataset-v1.json)

**Limitações.** Frases repetidas e templates compartilhados favorecem memorização.
Avaliar contra rótulos produzidos pelo mesmo gerador introduz circularidade.
O gold humano reduz a dependência dos rótulos do gerador, com exposição prévia
às frases registrada. A reserva de templates mede generalização dentro do
corpus sintético. [Auditoria de vazamento](../../docs/absa-splits.md)
