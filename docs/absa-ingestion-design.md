# Enriquecimento de aspectos na ingestão

A hipótese é que o filtro por aspecto extraído melhora a relevância dos
resultados em perguntas sobre reclamações específicas. O mesmo filtro pode
eliminar reviews relevantes quando o extrator omite ou confunde aspectos,
em especial atendimento e prazo de entrega.

O ponto de integração é a review validada, antes do chunking em
`IngestionPipeline`. O enriquecedor em lote recebe IDs e textos e devolve
um mapa de aspectos por review, validado pelo contrato ABSA. O checkpoint
253 fica fixado pelo hash do adapter e pela revisão da base. Cada chunk
herda os aspectos da review. O Chroma já grava `aspect_<nome>` e o
retriever já usa `aspect_<nome> = neg` ao receber um aspecto.

A execução experimental usa uma coleção separada e um cache por ID, hash
do texto, revisão do modelo e versão do contrato. Registrar mapas vazios
válidos e saídas inválidas separadamente. Na coleção experimental, um
mapa vazio significa ausência de aspectos detectados. Uma saída inválida
fica sem campos de aspecto, com o motivo registrado no relatório de
ingestão. Concluir a carga da coleção antes de apontar consultas para ela.

Comparar três condições com as mesmas reviews, embeddings, chunks,
filtros de restaurante e período, limiar e conjunto de perguntas:

| Condição | Metadados e filtro |
| --- | --- |
| Controle | Busca sem filtro por aspecto |
| Referência sintética | Filtro com aspectos do gerador |
| Extrator | Mesmo filtro com aspectos do checkpoint 253 |

Usar as perguntas com aspecto explícito e os IDs de relevância já
congelados. Reportar hit@k, recall@k e precisão@k, placar por pergunta e
quantas reviews relevantes o filtro excluiu. Mostrar separadamente casos
de lista vazia e a cobertura de extração. Para atribuir o ganho ao filtro,
manter as demais configurações iguais. A decisão de ativar o filtro
depende dos ganhos de precisão e das perdas de recall observadas.

A B2W mede transferência de domínio em avaliação separada. O corpus RAG
continua composto pelo split de reviews de restaurantes do projeto.
