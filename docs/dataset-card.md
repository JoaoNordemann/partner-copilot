# Ficha dos dados

O corpus do PartnerCopilot contém 3.000 avaliações sintéticas de delivery em português. Serve para testar ingestão, busca, geração com fontes e extração de aspectos. O gerador usou seed 42, janela de 90 dias e data final 2026-11-01. O corpus e o treino ABSA não contêm dados do iFood.

Templates repetidos e convenções compartilhadas entre treino, rótulos e relevância favorecem a memorização. O conjunto com anotação humana e a reserva de templates ajudam a distinguir esses efeitos dentro do corpus sintético. Ainda falta avaliação em textos reais de restaurantes. [Ficha ABSA e splits](../data/absa/README.md) · [Proveniência dos resultados](../reports/final-results-v1/manifest.json)

## Avaliação externa B2W

A B2W contém avaliações reais de e-commerce usadas exclusivamente para avaliar transferência de domínio. O projeto preserva os IDs, as anotações próprias e as métricas. Os textos da B2W não são redistribuídos. A licença MIT do código não concede direitos sobre a B2W. [Origem, licença e protocolo](absa-external-evaluation.md)
