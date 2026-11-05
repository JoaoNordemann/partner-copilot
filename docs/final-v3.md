# Rodada final V3 congelada

## Motivo

As 14 rejeicoes de citacao de D foram formato e fidelidade de ID: listas em um
colchete, marcadores/tags/frases e IDs corrompidos. Nenhum ID existente fora do
contexto foi encontrado nesses casos. Nao registrar como modelo inventou citacoes.
O retry de D nao recuperou nenhuma rejeicao e permanece descartado do fluxo normal.

| Estrategia | Aceitas pelo parser | Aceitas e plenamente sustentadas/alinhadas na leitura por IA |
| --- | --- | --- |
| C/D, mesmas 27 saidas originais do LLM | 2/27 | 1/2 aceitas: q05 |
| JSON v1, dez perguntas novas | 7/10 | 4/7 aceitas: n01, n04, n05, n07 |

O criterio pleno exclui n06 pela reformulacao imprecisa, n09 pelo evento sem apoio
e n10 pela abstencao semantica com flag errada, embora a ausencia de CNPJ seja
compativel com o contexto. Sao amostras pequenas, perguntas de dificuldades
diferentes e leitura por Codex/IA, nao prova causal nem gold humano independente.

## Mudancas declaradas

- Prompt partner-copilot-v3 mais curto; parser-v3 com manifesto de hashes.
- Primeiro objeto JSON completo via JSONDecoder.raw_decode, mesmo com objetos
  aninhados e chaves dentro de strings. Nao parar a geracao no primeiro }.
- A saida deve comecar com objeto JSON apos whitespace. Nao retirar introducoes
  ou code fences. Texto posterior e ignorado para a resposta, mas preservado na
  saida bruta e registrado em trailing_text_ignored/ignored_suffix_chars.
- Consistencia estrutural: abstem=true se e somente se afirmacoes esta vazia.
  Essa regra JA existia. Ela nao entende que uma frase como nao ha CNPJ e recusa;
  o caso abstem=false com afirmacao de ausencia ainda pode passar estruturalmente.
- Cada afirmacao traz fontes, cada qual com review_id e trecho. O trecho nao vazio
  deve ocorrer literalmente na review citada entre os documentos enviados. Nao
  normalizar acentos, espacos ou caixa. IDs e trechos sao verificados separadamente.
- O codigo monta [id]. Sem retry. Corpus e limiar permanecem iguais.
- Ate 8 reviews no contexto, retrieval_k=8 e min_score=0.25. max_new_tokens=512
  acomoda o JSON com trechos; temperatura zero, seed 42, mesmo Mistral NF4.

Essas alteracoes sao um pacote conjunto, nao ablacoes isoladas. A janela de 32768
nao estava esgotada: B teve prompts de 711 a 1236 tokens (mediana 1143), JSON v1 de
638 a 1020 (mediana 845), e D de 863 a 1831 (mediana 1483). Nao confundir contagem
de caracteres de template com tokens reais incluindo contexto e saida anterior.
Com o mesmo ranking, oito fontes podem recuperar o caso q01 na posicao 6; nao
resolvem q13, cuja fonte foi cortada por min_score.

## Limite da prova literal

Trecho existente nao prova entailment: o modelo ainda pode anexar uma frase real
sobre sabor a uma afirmacao inventada sobre exame laboratorial. Isso PASSA no teste
literal, mas falha na leitura factual. Ha um teste unitario explicito desse limite.
A regra rejeita citações literais inventadas, nao garante eliminar toda variante
de n09 e nao detecta automaticamente a irrelevancia de q23.

## Auditoria semantica anterior

D tinha 22/24 respondiveis com fonte rotulada relevante no contexto, 23/24 antes
do corte para cinco; JSON v1 tinha 7/7. A leitura das 24 respondiveis de D encontrou
8/24 recusas claras com evidencia rotulada e 2/24 negacoes parciais, separadas.
q24 tem ambiguidade de preco/porcao; excluindo-a, sao 7/24 claras conservadoras.
A taxa formal de 1/24 so contava q13, nao todas as recusas em saidas rejeitadas.
Origem: IA, criterios e cada caso em semantic-refusal-audit.md/JSON nos resultados D.

## Protocolo e congelamento

Prompt/parser foram congelados antes de criar n11-n20, dez perguntas com tres
negativas. Nenhuma inferencia exploratoria nas perguntas novas. Os testes de
geracao usam fixtures inventadas. Perguntas nao foram exibidas no preflight.
Sao perguntas novas no mesmo corpus conhecido, com rotulos textuais definidos por
IA; nao sao anotacao humana cega, nem holdout independente de documentos. Criar
perguntas requer conhecer seu texto, portanto nao alegar cegamento independente
do autor. Nao ajustar prompt, parser ou configuracao apos ver a rodada final.

Executar primeiro n11-n20 e depois as 30 originais com contaminated=true, no mesmo
processo e modelo carregado uma vez. Arquivos e resumos distintos. As antigas sao
registro de desenvolvimento, nao evidencia independente. A mistura de modelo,
contexto e parser novo impede atribuir o ganho a uma mudanca isolada.

## Kaggle

Importe partner-copilot-V3.ipynb como NOVO notebook, GPU/Internet ligados, kernel
novo e Secret HF_TOKEN habilitado. Nao precisa anexar B/D ou resultados antigos:
os dados congelados vem do GitHub. O codigo novo deve estar publicado antes de clonar.
O preflight mostra apenas 10/3 novas e 30/6 contaminadas, sem texto das perguntas.
Execute a celula final uma vez; nao altere as versoes depois de inspecionar respostas.

```bash
python scripts/evaluate_final_v3.py --output-dir /caminho/v3 --check-only
python scripts/evaluate_final_v3.py --output-dir /caminho/v3 --suite both --resume
python scripts/evaluate_final_v3.py --output-dir /caminho/v3 --suite both --summarize-only
```

Salvar JSONL, summary e review de cada grupo. Checkpoint com flush/fsync por
pergunta; retomada pula registros completos e exige a mesma identidade. Uma
pergunta interrompida antes de salvar pode precisar ser executada ao retomar;
nao ha retry corretivo automatico. O template de leitura nao e sobrescrito se existir.

Reportar: schema do primeiro objeto, sufixos ignorados, IDs no contexto, trechos
literais, abstencao correta/indevida, evidencia no contexto e sustentacao/pertinencia
por leitura. Ter trecho literal nao preenche automaticamente factualidade.
Nenhuma inferencia real de V3 foi executada no PC durante a implementacao.
