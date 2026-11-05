# Versionamento de prompt e parser

Os eixos sao independentes: partner-copilot-v1 ou partner-copilot-v2 para prompt;
parser-v1 ou parser-v2 para parser. Defaults permanecem v1/v1.
O parser original foi extraido sem mudanca de comportamento para output_v1.py;
output.py mantem a API parse_generation e seleciona a versao por parametro keyword.
O manifesto parser-manifest.json verifica hashes do codigo usado, inclusive a
dependencia v1 de parser-v2. Templates antigos conservam seus hashes.

Parser v2 normaliza somente a sequencia barra invertida + underscore antes de validar.
Isso tambem normaliza o marcador escapado, mas ele ainda precisa ser a saida inteira.
Nao remove introducoes, nao repara sintaxe review_id=, nao aceita fontes inventadas,
nao faz inferencias semanticas e nao tenta gerar de novo. A saida bruta e preservada
pelo runner; a resposta aceita pode ter underscores normalizados.

| Experimento | Prompt | Parser |
| --- | --- | --- |
| Referencia | partner-copilot-v1 | parser-v1 |
| Apenas parser | partner-copilot-v1 | parser-v2 |
| Apenas prompt | partner-copilot-v2 | parser-v1 |
| Combinacao | partner-copilot-v2 | parser-v2 |

Use arquivos de saida distintos e mantenha retrieval, k, limiar, seed e modelo fixos.
Revalidar saidas antigas com parser novo e uma analise derivada, nao uma nova inferencia;
um runner de replay nao faz parte desta alteracao. Nunca sobrescrever a v1.

A identidade schema 2 inclui parser_version, parser_sha256 e prompt_sha256.
Uma retomada antiga schema 1 sera recusada como experimento diferente. O runner
continua permitindo resumir os artefatos antigos sem modificar suas linhas.

v2 foi criada depois de ver a v1 nas mesmas 30 perguntas. E ajuste sobre o conjunto
de desenvolvimento, nao resultado de teste independente. O exemplo de adesivo e
inventado e nao e fonte de evidencia. Nao ha resultado real de GPU para v2 ainda.
