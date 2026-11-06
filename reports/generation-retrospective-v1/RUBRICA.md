# Rubrica retrospectiva de sustentação v1

Registrada antes de aplicar os novos julgamentos desta consolidação. Nenhuma nova
inferência, ajuste de prompt, parser, contexto ou limiar será executado.

## Unidade e objeto da leitura

Unidade: (experimento, question_id), nunca somente question_id. C é prompt-v2 com
parser-v2 sobre as saídas de B, não um prompt chamado C. D preserva o resultado final
após no máximo uma correção. V3 antiga e v3 nova são coortes distintas.

Avaliar o conteúdo da resposta candidata, mesmo rejeitada pelo parser, diante da
pergunta e das reviews completas realmente enviadas. Em JSON interpretável, avaliar
as afirmações do primeiro objeto e registrar separadamente texto ignorado/sufixo;
isso não autoriza mudar parsers antigos nem suas métricas. Em texto livre avaliar
a saída inteira; marcador misturado não elimina afirmações presentes. Não atribuir
fatos de uma review a outra nem usar evidência fora do contexto para justificar a
resposta. Fontes relevantes fora do contexto são diagnóstico de retrieval.

## Três níveis de sustentação

- sustentada: todas as afirmações materiais têm apoio no contexto; atribuições e
  polaridade estão corretas; não há extrapolação factual importante. Recusa por
  falta de evidência é sustentada quando realmente falta evidência no contexto.
- parcial: há núcleo factual apoiado, mas também extrapolação, generalização,
  atribuição ambígua ou afirmação material sem apoio; explicar exatamente a parte.
- sem_suporte: núcleo contradiz as reviews, inventa o fato principal, troca o aspecto
  que fundamenta a conclusão ou nega evidência explícita presente.

Erros de idioma/redação ou transcrição de trecho não mudam sustentação sozinhos,
se preservam inequivocamente o fato; ficam em observações e métricas de formato.
Uma resposta pode ser sustentada e responder a outro assunto.

## Pergunta separada: responde à pergunta?

responde_pergunta: sim / parcial / nao. Sim atende ao fato e escopo pedidos, inclusive
recusa justificada. Parcial atende só parte do pedido. Nao troca o assunto, inverte
o escopo ou recusa apesar de haver evidência explícita. Não inferir pertinência do
fato de o ID ou trecho ser válido.

abstencao: adequada / indevida / nao_se_aplica. Julgar semanticamente, inclusive
recusa sem marcador ou com schema inválido. Falhas de execução não são recusas.
Casos sem LLM são lidos separadamente e não entram na sustentação do modelo.

## Escopo fixo da nova leitura de IA

v1: q09, q22 e q13 (controle sem LLM). C: q05 e q23 (as duas aceitas).
D: q05, q09, q22 e q23. JSON v1: n02, n03, n09, n10.
V3 antiga: q09, q21, q23. V3 nova: todas n11–n20.
Publicar contagens somente sobre essa seleção e com denominador de lidas; não
estimar acurácia integral de uma versão com amostra escolhida por falhas.
Revisões antigas permanecem preservadas; não remapear rótulos antigos por código
como se fossem releitura sob esta rubrica.

## Revisão humana assistida no chat

João lê pergunta, resposta bruta e reviews inteiras do contexto. Registra sustentação,
responde_pergunta, abstencao e justificativa. Mostrar primeiro sua leitura, depois
comparar com o julgamento de IA; como julgamentos anteriores já foram expostos,
esta revisão é assistida e não cega. Só registrar origem humana após resposta real.

Contar unidades distintas lidas por João; concordância exata primária exige os
mesmos rótulos de sustentação E responde_pergunta, no mesmo experimento/pergunta.
Reportar também concordância separada em cada eixo, sem substituir por um percentual
único de qualidade. Denominador é número de pares efetivamente comparáveis; zero
revisões significa pendente, não 0% de concordância. Preservar desacordos e notas.

LLM-as-judge não será executado nesta etapa. Se futuramente autorizado, será um
experimento separado, validado contra os rótulos humanos deste mesmo conjunto,
com concordância e limitações: preferência por comprimento, pelo próprio modelo,
ordem/posição e contaminação por instruções. Baixa concordância não autoriza usar o
juiz como substituto; definir antes um critério de aceitação ou descartar o juiz.
