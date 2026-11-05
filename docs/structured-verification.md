# Verificacao da saida JSON

Estrategia: partner-copilot-json-v1 + parser-json-v1. Arquivos anteriores v1/v2 e D
permanecem preservados. Retry foi descartado, e o fluxo novo chama o modelo uma
vez por pergunta com contexto. Schema nao garante veracidade ou pertinencia.

## Contrato

```json
{"abstem": false, "afirmacoes": [{"texto": "Uma afirmacao sustentada.", "review_ids": ["ID_EXATO_DO_CONTEXTO"]}]}
```

Sem evidencia: {"abstem":true,"afirmacoes":[]}. O objeto precisa ser JSON estrito,
sem code fences, introducao ou chaves extras. Pydantic rejeita tipos coercivos,
chaves duplicadas, NaN e inconsistencias. Os IDs devem ser exatos e existir no
contexto. O codigo gera as referencias [id]; o modelo nao formata citacoes.
Nao ha reparo automatico ou nova tentativa. Os defaults legados permanecem para
reproducao; o runner e o notebook novos escolhem explicitamente o par JSON.

## Dados e congelamento

Dez perguntas novas em data/eval/json-verification-v1, sete respondiveis e tres
negativas. O manifesto congela perguntas, corpus e prompt por hash. O corpus e
exatamente o mesmo conjunto conhecido de 100 reviews de human-v2. Rotulos novos
foram definidos por IA por leitura textual, nao pelos aspectos do gerador; ainda
nao sao gold humano independente. Confirmacao humana pode ser registrada em
arquivo separado sem alterar o snapshot da primeira rodada.

O prompt foi congelado antes de criar as dez perguntas. Nao usar as 30 antigas
para avaliar esse prompt nem ajustar instrucoes apos ver as dez novas sem declarar
uma nova versao e novo protocolo. Isto e checagem fora das perguntas anteriores,
nao um holdout independente de documentos. Nao executar smoke test de ajuste numa
dessas perguntas antes da rodada, nem alterar parametros entre perguntas.

## Kaggle

Importe notebooks/partner-copilot-JSON.ipynb como novo notebook. Ative GPU e Internet,
habilite o Secret HF_TOKEN e use kernel novo. O codigo precisa estar publicado no
GitHub antes de clonar. Nao precisa anexar B ou D: corpus e perguntas novas vem do
repositorio. O notebook verifica dez perguntas e tres negativas antes da inferencia.

```bash
python scripts/evaluate_structured_generation.py --output /caminho/json-verification.jsonl --check-only
python scripts/evaluate_structured_generation.py --output /caminho/json-verification.jsonl --resume
python scripts/evaluate_structured_generation.py --output /caminho/json-verification.jsonl --summarize-only
```

A inferencia real exige CUDA. Reconstrucao de indice isolado e temporario, modelo
Mistral NF4 carregado uma vez, seed fixa, temperatura zero. Flush/fsync apos cada
pergunta. Retomada exige a mesma identidade e nao repete perguntas completas.
Nao ha retry de contrato. Uma pergunta em andamento no instante da queda pode
precisar ser executada ao retomar; nao ha tentativa corretiva escondida.

## Medidas separadas

1. Schema valido: entre chamadas do LLM, inclusive chamadas com saida invalida.
2. Abstencao correta: entre as tres negativas, incluindo abstencao por retrieval
   vazio; reportar tambem recusa indevida nas sete respondiveis.
3. IDs no contexto: entre saidas com schema valido e afirmacoes (abstencoes nao
   precisam de fontes e ficam fora desse denominador).
4. Sustentacao factual e pertinencia: leitura do texto e fontes; nasce pendente,
   sem taxa automatica. O template de revisao tem colunas separadas de parser e
   conteudo, e nao e sobrescrito se ja existir.

Registrar tambem erros, chamadas, contexto recebido, tokens, latencia e VRAM.
As taxas com denominador zero sao nulas. O resumo so publica taxas finais com as
dez tentativas completas. Preservar JSONL, resumo e revisao no ZIP e ler as dez
respostas (incluindo as tres negativas) antes de concluir qualidade.

Se JSON tambem falhar, o proximo experimento sera decodificacao com gramatica ou
JSON restrito; modelo alternativo e atribuicao de fontes por codigo sao opcoes
posteriores. Nao foram implementados nem medidos nesta etapa.
