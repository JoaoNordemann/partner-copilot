# Base pública externa: B2W-Reviews01

## Escolha e licença verificada

Escolhida uma única base: **B2W-Reviews01**, de reviews de produtos em português brasileiro,
originalmente coletadas na Americanas.com entre janeiro e maio de 2018.
Crédito: **B2W Digital; Livy Real, Marcio Oshiro e Alexandre Mafra (STIL 2019)**.

- Catálogo HF: https://huggingface.co/datasets/ruanchaves/b2w-reviews01
- Fonte original: https://github.com/americanas-tech/b2w-reviews01
- Revisão fixa: `4639429ec698d7821fc99a0bc665fa213d9fcd5a`.
- Evidência da licença: https://github.com/americanas-tech/b2w-reviews01/blob/4639429ec698d7821fc99a0bc665fa213d9fcd5a/README.md#licensing
- Termos: https://creativecommons.org/licenses/by-nc-sa/4.0/deed.pt-br

**Licença adotada: CC BY-NC-SA 4.0.** Exige atribuição, uso não comercial e
compartilhamento de adaptações distribuídas sob a mesma licença, com indicação das mudanças.
A licença foi conferida no README original antes do download e da seleção.
O catálogo HF declara CC BY 4.0, em divergência com a fonte original. Não usamos esse
metadado do espelho como autorização para retirar as restrições NC e SA.

Uso adotado: estudo e avaliação local não comercial. Esses termos não autorizam incorporar
automaticamente os textos a um produto comercial. A licença MIT declarada para o código do
PartnerCopilot não substitui a licença dos dados externos.

O carregador do HF aponta para o CSV da revisão original acima. Baixamos esse CSV diretamente,
sem executar o script remoto nem instalar `datasets`. O arquivo fixado usa delimitador vírgula,
como confirmado pelo cabeçalho; o conselho de ponto e vírgula do README original não se aplica
à leitura desse snapshot.

## Arquivos locais e separação do RAG

Tudo foi organizado em `data/external/b2w_reviews01/`:

| Arquivo | Finalidade |
|---|---|
| `B2W-Reviews01.csv` | Fonte integral, sem alterações |
| `SOURCE_README.md` | Evidência local da licença e da origem |
| `reviews_sample.jsonl` | 200 textos reais selecionados |
| `manifest.json` | URLs, revisão, hashes, seed, critérios e contagens |
| `LICENSE.txt` | Atribuição, licença e indicação das transformações |

`data/external/` continua ignorado pelo Git. Nem os textos, nem o CSV integral são
publicados automaticamente nos commits; o script e esta documentação permitem reproduzi-los.
O CSV integral inclui campos de perfil de avaliadores e permanece apenas na cópia local.
A amostra não exporta IDs de avaliadores, nascimento, gênero, localização ou IDs de produtos.

O preparador não importa Chroma nem instancia o pipeline de ingestão. Os registros usam
`external_id`, `source_row`, `domain="ecommerce"`, `text`, `overall_rating` e
`annotation_status="unannotated"`. Não recebem restaurant_id, bairro, category ou aspectos
fictícios para caber no schema do restaurante. Os testes verificam que esses registros são
rejeitados pelo loader do RAG antes de qualquer upsert.

## Amostragem reproduzível

- Fonte: **132.373 registros**.
- Amostra: **200 textos únicos**, 40 por nota de 1 a 5, seed **42**.
- Ranking: SHA-256 de seed + separador NUL + texto normalizado, dentro de cada nota.
- Normalização somente para deduplicação/ranking: casefold e compactação de espaços.
- Texto exportado preserva ortografia, caixa, acentos, pontuação e espaços internos;
  apenas espaços externos são removidos.
- Comprimento elegível: 20 a 2.000 caracteres.
- Exclusões: 3.298 por comprimento, 70 por sinais óbvios de contato e 2.387 duplicatas
  normalizadas, contadas nessa ordem. O filtro de contato não é uma garantia de anonimização.
- Todas as cinco cotas foram preenchidas sem repetição nem reposição.

As notas originais somam: 1=27.369, 2=8.389, 3=16.315, 4=32.345, 5=47.955.
A amostra balanceada é intencional para diagnóstico; não representa a distribuição natural
nem deve ser usada para estimar satisfação populacional.

SHA-256 do CSV:
`821fb0bf9f7230b0fba4e4f9fadd75a66d1a9ff0b1657810791d33007eb2ab38`

SHA-256 da amostra JSONL:
`97b813093cda3e33fc6a07e4f81075e181da58d3173c056f8d9ecb00d560f443`

## Uso para aspectos e vocabulário

A nota geral **não é rótulo de aspecto**. A base selecionada não tem anotações ABSA prontas.
A amostra permite inspecionar saídas do extrator; métricas de precisão e recall exigem
anotação humana de referência. Avaliações de produto não devem virar avaliações de sabor
por coerção de taxonomia. Menções a entrega, preço e atendimento podem ser comparadas;
aspectos específicos de produto precisam ser identificados como fora da taxonomia quando
não houver correspondência com os aspectos de restaurante.

Na inspeção aparecem opiniões mistas, produto não recebido, defeito, mensagens em caixa alta,
acentos omitidos, palavras juntas e pontuação irregular. Isso fornece material de realismo
sem editar os textos reais nem copiá-los para templates do gerador nesta implementação.

Se a amostra for usada para ajustar vocabulário ou prompts, ela será um conjunto exploratório,
não um teste cego final. Reserve textos independentes antes de reportar desempenho final.
Não foram executados extrator ou fine-tuning nesta preparação.

## Reproduzir

```powershell
python scripts/prepare_external_reviews.py --seed 42 --per-rating 40 --time-budget-minutes 10
```

O script verifica a evidência de licença antes de usar o CSV e confere o checksum do snapshot.
Reutiliza arquivos locais completos e reproduz a mesma amostra. O manifesto tem timestamp e
tempo de execução variáveis; os bytes da amostra são determinísticos. Não precisa de token HF
nem GPU. Downloads têm timeout, limite de tamanho e publicação de arquivo concluído por rename.

A preparação foi concluída dentro do teto de 1h30. O limite padrão do comando é de 10 minutos,
com verificação de prazo no download e na seleção; não há dependência bloqueante para o RAG.
