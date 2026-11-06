# Retrieval CPU: complete ablation matrix

Development benchmark: 30 exposed questions, 24 answerable; no generation measured.
Restaurant-only filtering; item/date filters are intentionally absent.
Metrics are macro over answerable questions. Empty precision slots count as zero.
Random rows use the per-question mean over 200 seeds, not a single random draw.
No tuning or automatic default changes. All attempted models are listed in results.json.

| Policy | Method | Filter | k | Hit | Capped recall | Classic recall | MRR | Precision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ranking | english | sem_filtro | 1 | 0.0833 | 0.0833 | 0.0556 | 0.0833 | 0.0833 |
| ranking | english | sem_filtro | 3 | 0.2500 | 0.1319 | 0.1319 | 0.1528 | 0.0833 |
| ranking | english | sem_filtro | 5 | 0.4167 | 0.2583 | 0.2552 | 0.1882 | 0.1000 |
| ranking | english | sem_filtro | 8 | 0.5000 | 0.3785 | 0.3785 | 0.2003 | 0.0885 |
| ranking | english | sem_filtro | 12 | 0.5417 | 0.4340 | 0.4340 | 0.2050 | 0.0694 |
| ranking | english | restaurante | 1 | 0.2083 | 0.2083 | 0.1163 | 0.2083 | 0.2083 |
| ranking | english | restaurante | 3 | 0.5417 | 0.3681 | 0.3451 | 0.3403 | 0.2083 |
| ranking | english | restaurante | 5 | 0.6667 | 0.4715 | 0.4622 | 0.3674 | 0.2000 |
| ranking | english | restaurante | 8 | 0.8750 | 0.7347 | 0.7347 | 0.3974 | 0.2135 |
| ranking | english | restaurante | 12 | 0.9583 | 0.9479 | 0.9479 | 0.4062 | 0.1944 |
| ranking | multilingual | sem_filtro | 1 | 0.1667 | 0.1667 | 0.0972 | 0.1667 | 0.1667 |
| ranking | multilingual | sem_filtro | 3 | 0.3333 | 0.1806 | 0.1750 | 0.2292 | 0.1111 |
| ranking | multilingual | sem_filtro | 5 | 0.4167 | 0.2514 | 0.2514 | 0.2500 | 0.1000 |
| ranking | multilingual | sem_filtro | 8 | 0.5000 | 0.3347 | 0.3347 | 0.2629 | 0.0729 |
| ranking | multilingual | sem_filtro | 12 | 0.6250 | 0.4628 | 0.4628 | 0.2746 | 0.0729 |
| ranking | multilingual | restaurante | 1 | 0.2917 | 0.2917 | 0.1247 | 0.2917 | 0.2917 |
| ranking | multilingual | restaurante | 3 | 0.7500 | 0.5347 | 0.4816 | 0.4792 | 0.3194 |
| ranking | multilingual | restaurante | 5 | 0.9167 | 0.7465 | 0.7340 | 0.5167 | 0.3250 |
| ranking | multilingual | restaurante | 8 | 1.0000 | 0.9274 | 0.9274 | 0.5296 | 0.2708 |
| ranking | multilingual | restaurante | 12 | 1.0000 | 1.0000 | 1.0000 | 0.5296 | 0.2014 |
| ranking | keyword | sem_filtro | 1 | 0.0833 | 0.0833 | 0.0347 | 0.0833 | 0.0833 |
| ranking | keyword | sem_filtro | 3 | 0.2917 | 0.2431 | 0.2431 | 0.1806 | 0.1389 |
| ranking | keyword | sem_filtro | 5 | 0.4167 | 0.3347 | 0.3347 | 0.2118 | 0.1083 |
| ranking | keyword | sem_filtro | 8 | 0.5000 | 0.4160 | 0.4160 | 0.2257 | 0.0990 |
| ranking | keyword | sem_filtro | 12 | 0.5417 | 0.4576 | 0.4576 | 0.2303 | 0.0694 |
| ranking | keyword | restaurante | 1 | 0.2500 | 0.2500 | 0.1316 | 0.2500 | 0.2500 |
| ranking | keyword | restaurante | 3 | 0.6250 | 0.5069 | 0.4552 | 0.4167 | 0.3194 |
| ranking | keyword | restaurante | 5 | 0.7500 | 0.5736 | 0.5642 | 0.4437 | 0.2417 |
| ranking | keyword | restaurante | 8 | 0.8750 | 0.7424 | 0.7424 | 0.4646 | 0.2135 |
| ranking | keyword | restaurante | 12 | 1.0000 | 1.0000 | 1.0000 | 0.4765 | 0.2014 |
| ranking | random | sem_filtro | 1 | 0.0238 | 0.0238 | 0.0090 | 0.0238 | 0.0238 |
| ranking | random | sem_filtro | 3 | 0.0712 | 0.0347 | 0.0298 | 0.0439 | 0.0245 |
| ranking | random | sem_filtro | 5 | 0.1187 | 0.0534 | 0.0520 | 0.0547 | 0.0247 |
| ranking | random | sem_filtro | 8 | 0.1815 | 0.0825 | 0.0825 | 0.0638 | 0.0247 |
| ranking | random | sem_filtro | 12 | 0.2569 | 0.1228 | 0.1228 | 0.0711 | 0.0248 |
| ranking | random | restaurante | 1 | 0.2004 | 0.2004 | 0.0858 | 0.2004 | 0.2004 |
| ranking | random | restaurante | 3 | 0.4713 | 0.2873 | 0.2501 | 0.3167 | 0.1981 |
| ranking | random | restaurante | 5 | 0.6496 | 0.4208 | 0.4109 | 0.3572 | 0.1974 |
| ranking | random | restaurante | 8 | 0.8233 | 0.6458 | 0.6458 | 0.3827 | 0.1954 |
| ranking | random | restaurante | 12 | 0.9775 | 0.9549 | 0.9549 | 0.3978 | 0.1934 |
| operational | english | sem_filtro | 1 | 0.0833 | 0.0833 | 0.0556 | 0.0833 | 0.0833 |
| operational | english | sem_filtro | 3 | 0.2500 | 0.1319 | 0.1319 | 0.1528 | 0.0833 |
| operational | english | sem_filtro | 5 | 0.4167 | 0.2583 | 0.2552 | 0.1882 | 0.1000 |
| operational | english | sem_filtro | 8 | 0.5000 | 0.3785 | 0.3785 | 0.2003 | 0.0885 |
| operational | english | sem_filtro | 12 | 0.5417 | 0.4340 | 0.4340 | 0.2050 | 0.0694 |
| operational | english | restaurante | 1 | 0.2083 | 0.2083 | 0.1163 | 0.2083 | 0.2083 |
| operational | english | restaurante | 3 | 0.5417 | 0.3681 | 0.3451 | 0.3403 | 0.2083 |
| operational | english | restaurante | 5 | 0.6667 | 0.4715 | 0.4622 | 0.3674 | 0.2000 |
| operational | english | restaurante | 8 | 0.8750 | 0.7347 | 0.7347 | 0.3974 | 0.2135 |
| operational | english | restaurante | 12 | 0.9583 | 0.9340 | 0.9340 | 0.4062 | 0.1910 |
| operational | multilingual | sem_filtro | 1 | 0.1667 | 0.1667 | 0.0972 | 0.1667 | 0.1667 |
| operational | multilingual | sem_filtro | 3 | 0.3333 | 0.1806 | 0.1750 | 0.2292 | 0.1111 |
| operational | multilingual | sem_filtro | 5 | 0.4167 | 0.2514 | 0.2514 | 0.2500 | 0.1000 |
| operational | multilingual | sem_filtro | 8 | 0.5000 | 0.3347 | 0.3347 | 0.2629 | 0.0729 |
| operational | multilingual | sem_filtro | 12 | 0.6250 | 0.4628 | 0.4628 | 0.2746 | 0.0729 |
| operational | multilingual | restaurante | 1 | 0.2917 | 0.2917 | 0.1247 | 0.2917 | 0.2917 |
| operational | multilingual | restaurante | 3 | 0.7083 | 0.4792 | 0.4260 | 0.4653 | 0.2917 |
| operational | multilingual | restaurante | 5 | 0.8750 | 0.6687 | 0.6562 | 0.5028 | 0.2917 |
| operational | multilingual | restaurante | 8 | 0.9583 | 0.7983 | 0.7983 | 0.5157 | 0.2292 |
| operational | multilingual | restaurante | 12 | 0.9583 | 0.8434 | 0.8434 | 0.5157 | 0.1632 |
| operational | keyword | sem_filtro | 1 | 0.0833 | 0.0833 | 0.0347 | 0.0833 | 0.0833 |
| operational | keyword | sem_filtro | 3 | 0.2917 | 0.2431 | 0.2431 | 0.1806 | 0.1389 |
| operational | keyword | sem_filtro | 5 | 0.3750 | 0.2931 | 0.2931 | 0.2014 | 0.1000 |
| operational | keyword | sem_filtro | 8 | 0.4583 | 0.3743 | 0.3743 | 0.2153 | 0.0938 |
| operational | keyword | sem_filtro | 12 | 0.5000 | 0.4160 | 0.4160 | 0.2199 | 0.0660 |
| operational | keyword | restaurante | 1 | 0.2083 | 0.2083 | 0.1264 | 0.2083 | 0.2083 |
| operational | keyword | restaurante | 3 | 0.5000 | 0.3958 | 0.3812 | 0.3403 | 0.2361 |
| operational | keyword | restaurante | 5 | 0.5417 | 0.4472 | 0.4472 | 0.3507 | 0.1667 |
| operational | keyword | restaurante | 8 | 0.5417 | 0.4681 | 0.4681 | 0.3507 | 0.1094 |
| operational | keyword | restaurante | 12 | 0.5417 | 0.4681 | 0.4681 | 0.3507 | 0.0729 |
| operational | random | sem_filtro | 1 | 0.0238 | 0.0238 | 0.0090 | 0.0238 | 0.0238 |
| operational | random | sem_filtro | 3 | 0.0712 | 0.0347 | 0.0298 | 0.0439 | 0.0245 |
| operational | random | sem_filtro | 5 | 0.1187 | 0.0534 | 0.0520 | 0.0547 | 0.0247 |
| operational | random | sem_filtro | 8 | 0.1815 | 0.0825 | 0.0825 | 0.0638 | 0.0247 |
| operational | random | sem_filtro | 12 | 0.2569 | 0.1228 | 0.1228 | 0.0711 | 0.0248 |
| operational | random | restaurante | 1 | 0.2004 | 0.2004 | 0.0858 | 0.2004 | 0.2004 |
| operational | random | restaurante | 3 | 0.4713 | 0.2873 | 0.2501 | 0.3167 | 0.1981 |
| operational | random | restaurante | 5 | 0.6496 | 0.4208 | 0.4109 | 0.3572 | 0.1974 |
| operational | random | restaurante | 8 | 0.8233 | 0.6458 | 0.6458 | 0.3827 | 0.1954 |
| operational | random | restaurante | 12 | 0.9775 | 0.9549 | 0.9549 | 0.3978 | 0.1934 |

## Primary comparison

Multilingual versus English, capped recall@5 without filter, no score cutoff.
Wins 4, ties 16, losses 4 / 24; mean delta -0.006944.

## Interpretation limits

This is not an independent test. Language suitability motivated the multilingual choice before this comparison.
No model is declared best by selecting a favorable k or metric after the run.
Capped recall changes denominator with k and need not increase. Classic recall and added relevant/irrelevant counts are in results.json.
Negative questions, abstention, random dispersion and all paired question-level deltas are in results.json.
Collections are rebuilt separately in a temporary isolated database; production Chroma is untouched.
Full candidate retrieval measures ranking, not production ANN latency. Elapsed time includes model load/download.
Question/corpus annotations retain their original provenance; no human-independent gold is claimed.
