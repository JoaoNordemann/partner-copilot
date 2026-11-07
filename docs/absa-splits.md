# Splits e vazamento de templates no ABSA

O [manifesto ABSA](../data/absa/splits-v1.json) fixa IDs, contagens, exclusões,
famílias reservadas e hashes dos insumos. Para montar os conjuntos, selecione
cada lista de `ids` no `train_pool` validado por `load_absa_train_pool()`. Use
texto como entrada e `aspects` como alvo. Mantenha `template_test` separado do
processo de treino e de escolha de checkpoint.

| Conjunto | Reviews | Uso |
| --- | ---: | --- |
| Gold | 100 | Teste final com rótulos anotados por IA às cegas aos rótulos do gerador. Revisão humana independente pendente |
| Treino | 1.263 | Ajuste do modelo com rótulos sintéticos |
| Validação | 140 | Acompanhar treino e escolher checkpoint, com pelo menos cinco exemplos de cada par aspecto/polaridade |
| Teste de templates reservados | 346 | Avaliação separada em reviews sintéticas com pelo menos uma família reservada |

Dos 2.037 registros do `train_pool`, foram removidas **96 repetições** em 60 grupos
com duplicatas de review inteira e **192 reviews com ambiguidade sinalizada**
entre os representantes restantes. Para duplicatas com alvo idêntico, preserva-se
o menor ID. Um conflito de alvos excluiria o grupo inteiro. O manifesto registra
as exclusões por ID e motivo. O filtro de ambiguidade cobre a diferença de sabor
sem julgamento e duas famílias de duração de entrega sem avaliação explícita.
É um filtro das famílias conhecidas, com escopo restrito a essas regras.

Os três splits derivados têm IDs e textos normalizados disjuntos. Nenhum dos
100 IDs do gold ou o ID em quarentena entrou no treino, validação ou teste
sintético. A auditoria textual usa o arquivo cego do gold, sem consultar seus
rótulos para selecionar famílias ou medir desempenho.

## Sobreposição literal

Dividir por ponto, exclamação, interrogação e quebra de linha. Normalizar
minúsculas, acentos e espaços. Manter nomes de pratos e números nesta métrica.
Uma frase conta como sobreposta se sua forma normalizada aparece no conjunto
comparado. Reportar ocorrências e formas distintas separadamente.

| Referência | Ocorrências do gold encontradas | Frases distintas encontradas |
| --- | ---: | ---: |
| `train_pool` original | 251/294 (85,4%) | 178/221 (80,5%) |
| Treino final | 207/294 (70,4%) | 145/221 (65,6%) |

A sobreposição continua alta após o recorte. O F1 agregado do gold pode refletir
memorização de frases e famílias. Os números acima medem exposição textual.

## Reserva de famílias

O gerador grava texto e rótulos. Para reconstruir as famílias, substituir nomes
de itens do cardápio e minutos por marcadores e casar as frases com as constantes
de templates do gerador. Aberturas e fechamentos genéricos ficam fora das
famílias de aspecto. A recuperação das famílias é conferida contra os rótulos
sintéticos de cada representante do `train_pool`.

Selecionar por hash com seed 2718 uma família observada em pelo menos cinco
reviews elegíveis para cada um dos 12 pares aspecto/polaridade. A seleção usa
apenas o `train_pool` após as exclusões. Toda review com uma família reservada
vai para `template_test`. Das demais, 140 formam a validação, com cobertura
mínima por par e ordem determinística. Os 1.263 registros restantes formam o
treino. As 12 famílias têm zero ocorrências no treino e na validação.

| Recorte em relação ao treino | Gold | Teste de templates reservados |
| --- | ---: | ---: |
| Só famílias vistas | 66 | 0 |
| Famílias vistas e inéditas na mesma review | 32 | 310 |
| Só famílias inéditas | 2 | 36 |

Na avaliação final, fazer uma passada no gold após escolher o checkpoint pela
validação. Reutilizar as mesmas previsões para F1 do gold completo e para os
recortes de famílias vistas, mistas e inéditas. Reportar contagens e o F1 com e
sem casos ambíguos conforme a decisão registrada. O grupo gold inteiramente
inédito tem duas reviews, então a comparação principal de templates inéditos
deve incluir o teste sintético reservado. Reportar suas 36 reviews inteiramente
inéditas separadamente das 310 mistas e explicitar a origem sintética dos alvos.

```powershell
python scripts/prepare_absa_splits.py --check
```

O comando recompõe o manifesto e verifica a alocação e os hashes. A auditoria
ocorreu antes do treino e da inferência de avaliação. O F1 fica para a avaliação final.
