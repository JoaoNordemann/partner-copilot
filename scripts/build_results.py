#!/usr/bin/env python
"""Build final result tables from committed artifacts; stdlib only, no model calls."""

import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT_COMMIT = "1f954b3fa3e73e2d4aca3ae896affd2f6300a6d8"
BEGIN = "<!-- BEGIN GENERATED RESULTS -->"
END = "<!-- END GENERATED RESULTS -->"
COLUMNS = [
    "Configuração / caso",
    "O que mede",
    "Conjunto / exposição",
    "n",
    "Resultado",
    "Contagens brutas",
    "Limitação",
]
EXPOSED = "human-v2 q01–q30; desenvolvimento exposto/contaminado"
LIMIT = "Conjunto pequeno e exposto; não é estimativa independente de generalização."
RPATH = "reports/retrieval-cpu-ablation-v1/results.json"
GPATH = "reports/generation-retrospective-v1/metrics.json"
HPATH = "reports/generation-retrospective-v1/human-review.jsonl"
APATH = "reports/generation-retrospective-v1/ai-review.jsonl"
CPATH = "reports/cost-latency-consolidation-v1/metrics.json"


def normalized(data: bytes) -> bytes:
    return data.decode("utf-8").replace("\r\n", "\n").encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Inputs:
    """Validate working files against the cited Git commit and preserve provenance."""

    def __init__(self, root: Path, commit: str):
        if not re.fullmatch(r"[a-f0-9]{40}", commit):
            raise ValueError("Use a full, immutable commit SHA")
        self.root, self.commit = root, commit
        self.files = {}
        self.cache = {}

    def read(self, path: str):
        if path not in self.cache:
            raw = (self.root / path).read_bytes()
            blob = subprocess.check_output(["git", "show", f"{self.commit}:{path}"], cwd=self.root)
            if normalized(raw) != normalized(blob):
                raise ValueError(f"Input differs from cited commit: {path}")
            self.files[path] = {
                "commit": self.commit,
                "sha256_bytes": sha(raw),
                "sha256_lf": sha(normalized(raw)),
            }
            text = raw.decode("utf-8")
            self.cache[path] = (
                [json.loads(line) for line in text.splitlines() if line.strip()]
                if path.endswith(".jsonl")
                else json.loads(text)
            )
        return self.cache[path]

    def verify_upstream(self, value: dict):
        for path, expected in value["source_sha256"].items():
            self.read(path)
            if self.files[path]["sha256_bytes"] != expected:
                raise ValueError(f"Upstream source checksum differs: {path}")


def number(value: float, digits: int = 4) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def fraction(value: dict) -> str:
    return f"{value['passed']}/{value['applicable']}" if value["applicable"] else "N/A"


def integer(value: float) -> int:
    rounded = round(value)
    if not math.isclose(value, rounded, abs_tol=1e-6):
        raise ValueError("A raw count must be integral")
    return rounded


def raw_counts(block: dict, repeats: int = 1) -> str:
    rows = [r for r in block["questions"] if not r["deve_abster"]]
    if len(rows) != len({r["id"] for r in rows}):
        raise ValueError("Duplicate question in result block")
    hits = integer(sum(r["hit_at_k"] for r in rows) * repeats)
    relevant = integer(sum(r["retrieved_relevant"] for r in rows) * repeats)
    noise = integer(sum(r["retrieved_irrelevant"] for r in rows) * repeats)
    return f"Hit {hits}/{len(rows) * repeats}; relevantes {relevant}; irrelevantes {noise}"


def metric_line(block: dict) -> str:
    s = block["summary"]
    return "; ".join(
        f"{label}={number(s[key])}"
        for label, key in [
            ("Hit", "hit_at_k"),
            ("recall limitado", "recall_capped_at_k"),
            ("recall clássico", "recall_classic_at_k"),
            ("MRR", "mrr_at_k"),
            ("precision", "precision_at_k"),
        ]
    )


def find_pair(report: dict, category: str, **match) -> dict:
    matches = [r for r in report["paired"][category] if all(r[k] == v for k, v in match.items())]
    if len(matches) != 1:
        raise ValueError("Paired comparison is missing or ambiguous")
    row = matches[0]
    pairs = [row] if "wins" in row else row["metrics"].values()
    for pair in pairs:
        if pair["wins"] + pair["ties"] + pair["losses"] != pair["questions"]:
            raise ValueError("Inconsistent paired totals")
    return row


def exposure(name: str) -> str:
    if name == "v3-new":
        return "n11–n20; limpo na execução congelada; corpus conhecido/rótulos IA"
    if name in ("json-v1", "JSON-v1"):
        return "n01–n10; contaminado nesta consolidação retrospectiva"
    return "q01–q30; contaminado por iterações anteriores"


def build_tables(inputs: Inputs) -> tuple[list[dict], dict]:
    retrieval = inputs.read(RPATH)
    generation = inputs.read(GPATH)
    humans = inputs.read(HPATH)
    ai = inputs.read(APATH)
    cost = inputs.read(CPATH)
    inputs.verify_upstream(generation)
    inputs.verify_upstream(cost)
    correction = inputs.read("reports/generation-kaggle-D/analysis.json")
    if not retrieval["complete"] or any(h["status"] != "completed" for h in humans):
        raise ValueError("Require complete recorded ablations and human review")
    tables = []

    def table(identifier, question, rows, paths):
        tables.append(
            {
                "id": identifier,
                "question": question,
                "columns": COLUMNS,
                "rows": rows,
                "inputs": sorted(set(paths)),
            }
        )

    # RQ1: every pre-registered k and both modes, not a favorable post-hoc slice.
    rows = []
    for mode in ("sem_filtro", "restaurante"):
        for k in retrieval["ks"]:
            for model in ("english", "multilingual"):
                block = retrieval["methods"][model][mode]["ranking"][str(k)]
                pair = find_pair(
                    retrieval,
                    "methods",
                    reference="english",
                    variant="multilingual",
                    policy="ranking",
                    mode=mode,
                    k=k,
                    metric="recall_capped_at_k",
                )
                counts = raw_counts(block)
                if model == "multilingual":
                    counts += (
                        f"; contra inglês V/E/D={pair['wins']}/{pair['ties']}/{pair['losses']}"
                    )
                rows.append(
                    [
                        f"{model}; {mode}; k={k}",
                        "Ranking cosseno sem corte de score",
                        EXPOSED,
                        "24 respondíveis de 30",
                        metric_line(block),
                        counts,
                        LIMIT,
                    ]
                )
    table(
        "01-embedding", "A troca de embedding inglês por multilíngue valeu a pena?", rows, [RPATH]
    )

    rows = []
    for model in retrieval["methods"]:
        for k in retrieval["ks"]:
            pair = find_pair(
                retrieval,
                "filters",
                method=model,
                policy="ranking",
                k=k,
                metric="recall_capped_at_k",
            )
            a = retrieval["methods"][model]["sem_filtro"]["ranking"][str(k)]
            b = retrieval["methods"][model]["restaurante"]["ranking"][str(k)]
            repeats = 200 if model == "random" else 1
            result = (
                f"recall limitado: "
                f"{number(a['summary']['recall_capped_at_k'])} → "
                f"{number(b['summary']['recall_capped_at_k'])}; delta "
                f"{number(pair['mean_delta'])}"
            )
            rows.append(
                [
                    f"{model}; k={k}",
                    "Efeito de filtrar somente restaurant_id",
                    EXPOSED,
                    "24 perguntas; 200 repetições" if repeats > 1 else "24 perguntas",
                    result,
                    f"V/E/D={pair['wins']}/{pair['ties']}/{pair['losses']}; sem: "
                    f"{raw_counts(a, repeats)}; com: {raw_counts(b, repeats)}",
                    "O filtro fornece escopo; item/data não são aplicados e o "
                    "efeito não isola entendimento semântico.",
                ]
            )
    table("02-filtro", "Quanto do desempenho depende do filtro por restaurante?", rows, [RPATH])

    rows = []
    for increment in retrieval["paired"]["k_increments"]:
        if increment["policy"] != "ranking":
            continue
        method, mode = increment["method"], increment["mode"]
        a, b = str(increment["from_k"]), str(increment["to_k"])
        left = retrieval["methods"][method][mode]["ranking"][a]["summary"]
        right = retrieval["methods"][method][mode]["ranking"][b]["summary"]
        pair = increment["metrics"]["recall_classic_at_k"]
        repeat = 200 if method == "random" else 1
        rows.append(
            [
                f"{method}; {mode}; {a}→{b}",
                "Ganho de recall clássico versus ruído ao ampliar k",
                EXPOSED,
                "24 perguntas; 200 repetições" if repeat > 1 else "24 perguntas",
                f"recall clássico "
                f"{number(left['recall_classic_at_k'])}→{number(right['recall_classic_at_k'])}; "
                f"precision "
                f"{number(left['precision_at_k'])}→{number(right['precision_at_k'])}",
                f"R "
                f"adicionais={integer(increment['additional_relevant'] * repeat)}; "
                f"I "
                f"adicionais={integer(increment['additional_irrelevant'] * repeat)}; "
                f"V/E/D={pair['wins']}/{pair['ties']}/{pair['losses']}",
                "Recall limitado muda de denominador com k; estes dados de "
                "retrieval não determinam o melhor contexto de geração.",
            ]
        )
    table("03-k", "Quando aumentar k deixa de compensar o ruído?", rows, [RPATH])

    rows = []
    for method, modes in retrieval["methods"].items():
        for mode in ("sem_filtro", "restaurante"):
            for policy in ("ranking", "operational"):
                for k in retrieval["ks"]:
                    block = modes[mode][policy][str(k)]
                    repeat = 200 if method == "random" else 1
                    extra = ""
                    if repeat > 1:
                        sd = block["aggregate_std_across_seeds"]["recall_capped_at_k"]
                        extra = f"; DP recall entre seeds={number(sd)}"
                    rows.append(
                        [
                            f"{method}; {mode}; {policy}; k={k}",
                            "Matriz completa com aleatório e palavras-chave",
                            EXPOSED,
                            "24 perguntas; 200 permutações" if repeat > 1 else "24 perguntas",
                            metric_line(block) + extra,
                            raw_counts(block, repeat),
                            "Seeds não são perguntas independentes; os cortes "
                            "operacionais dos métodos não são confiança equivalente.",
                        ]
                    )
    table("04-baselines", "O embedding acrescenta algo aos baselines baratos?", rows, [RPATH])

    rows = []
    for name, g in generation["experiments"].items():
        selected_ai = [r for r in ai if r["experiment"] == name and r["llm_called"]]
        selected_h = [r for r in humans if r["experiment"] == name]
        support_ai = sum(r["support"] == "sustentada" for r in selected_ai)
        support_h = sum(r["support"] == "sustentada" for r in selected_h)
        human_support = fraction({"passed": support_h, "applicable": len(selected_h)})
        pertinent_h = sum(
            r["support"] == "sustentada" and r["answers_question"] == "sim" for r in selected_h
        )
        human_relevant = fraction({"passed": pertinent_h, "applicable": len(selected_h)})
        rows.append(
            [
                name,
                "Schema, IDs, trecho, aceitação e conteúdo separados",
                exposure(name),
                f"{g['questions']} perguntas; {g['llm_outputs']} saídas; {g['no_llm']} sem LLM",
                f"schema {fraction(g['schema'])}; parser "
                f"{fraction(g['accepted'])}; IDs {fraction(g['ids'])}; "
                f"literal {fraction(g['quotes'])}",
                f"sustentadas IA {support_ai}/{len(selected_ai)} lidas; "
                f"humanas assistidas {human_support} ({len(selected_h)} lidas); "
                f"humanas sustentadas e pertinentes "
                f"{human_relevant}",
                "Denominadores variam por ramo; sustentação só cobre casos "
                "lidos e N/A não significa falha.",
            ]
        )
    table(
        "05-contrato",
        "Formato válido, fonte válida e conteúdo sustentado coincidem?",
        rows,
        [GPATH, APATH, HPATH],
    )

    b_rows = {
        r["question_id"]: r
        for r in inputs.read(
            "reports/generation-kaggle-v2/generation-kaggle-B-prompt-v2-parser-v1.jsonl"
        )
    }
    paths = {
        "v1": "reports/generation-kaggle-v1/generation-kaggle-v1.jsonl",
        "C": "reports/generation-kaggle-v2/generation-kaggle-C-parser-v2.jsonl",
        "D": "reports/generation-kaggle-D/generation-kaggle-D.jsonl",
        "json-v1": "reports/generation-json-v1/generation-json-v1.jsonl",
        "v3-old": "reports/final-v3/generation-v3-contaminated.jsonl",
        "v3-new": "reports/final-v3/generation-v3-new.jsonl",
    }
    rows = []
    for name, path in paths.items():
        source = inputs.read(path)
        if name == "C":
            source = [
                {
                    **b_rows[r["question_id"]],
                    **r,
                    "answer": r["parsed"]
                    if r["llm_called"]
                    else b_rows[r["question_id"]]["answer"],
                }
                for r in source
            ]
        negative = [r for r in source if r["deve_abster"]]
        positive = [r for r in source if not r["deve_abster"]]

        def abstains(row):
            return bool(row.get("answer") and row["answer"]["abstained"])

        correct = sum(abstains(r) for r in negative)
        model = sum(abstains(r) and r["llm_called"] for r in negative)
        calls = sum(r["llm_called"] for r in negative)
        empty = sum(abstains(r) and not r["llm_called"] for r in negative)
        undue = sum(abstains(r) for r in positive)
        errors = sum(r.get("error") is not None for r in source)
        evidence = generation["experiments"][name]["positive_context_evidence"]
        rows.append(
            [
                name,
                "Abstenção formal e presença de fonte relevante",
                exposure(name),
                f"{len(positive)} respondíveis; {len(negative)} negativas",
                f"evidência nas positivas {fraction(evidence)}; recusa "
                f"indevida formal {undue}/{len(positive)}",
                f"negativas abstidas {correct}/{len(negative)}; "
                f"LLM {model}/{calls} chamadas negativas; {empty} sem LLM; erros de "
                f"contrato {errors}/{len(source)}",
                "Recusas semânticas em saídas rejeitadas ficam fora da taxa "
                "formal; lista relevante não comprova fidelidade.",
            ]
        )
    table(
        "06-abstencao",
        "O sistema encontra evidência e se abstém quando necessário?",
        rows,
        [
            GPATH,
            *paths.values(),
            "reports/generation-kaggle-v2/generation-kaggle-B-prompt-v2-parser-v1.jsonl",
        ],
    )

    lookup = {(r["experiment"], r["question_id"]): r for r in ai}
    rows = []
    for h in humans:
        other = lookup[(h["experiment"], h["question_id"])]
        agrees = all(h[k] == other[k] for k in ("support", "answers_question"))
        rows.append(
            [
                f"{h['experiment']}/{h['question_id']}",
                "Sustentação e pertinência na revisão humana assistida",
                exposure(h["experiment"]) + "; seleção retrospectiva de entrevista",
                "1 caso",
                f"{h['support']}; responde={h['answers_question']}; "
                f"abstenção={h['semantic_abstention']}",
                f"leitura 1; concordância conjunta {int(agrees)}/1; {h['notes']}",
                "IA ajudou no enquadramento e houve exposição aos "
                "julgamentos; não é revisão cega nem acurácia global.",
            ]
        )
    table("07-revisao", "Quais falhas foram confirmadas na leitura humana?", rows, [HPATH, APATH])

    rows = []
    for name, g in cost["gpu_cohorts"].items():
        t = g["generation_seconds"]
        memory = g["vram_peak_allocated"]
        loads = ", ".join(number(x, 3) for x in g["load_seconds_distinct_attributes"])
        rows.append(
            [
                f"{name}; Kaggle/Tesla T4; {g['environment']['source_commit'][:7]}",
                "Latência de geração, carga e pico alocado NF4",
                exposure(name),
                f"{g['llm_outputs_measured']} chamadas",
                f"mediana/média/p95 "
                f"{number(t['median'], 3)}/{number(t['mean'], 3)}/"
                f"{number(t['p95_nearest_rank'], 3)} "
                f"s; carga {loads} s; pico {number(memory['GB'], 3)} GB / "
                f"{number(memory['GiB'], 3)} GiB",
                f"prompt {g['prompt_tokens']['sum']}; gerados "
                f"{g['generated_tokens']['sum']}; soma geração "
                f"{number(t['sum'], 3)} s",
                "Carga é atributo repetido, reservado difere de alocado e o "
                "tempo não é benchmark da máquina local.",
            ]
        )
    for name, c in cost["cpu"]["runs"].items():
        rows.append(
            [
                f"{name}; PC Windows / CPU não identificada",
                "Tempo total histórico da ablação CPU",
                EXPOSED,
                f"{c['corpus_documents']} documentos; {c['queries']} "
                f"perguntas x {c['filter_modes']} modos",
                f"execução inteira {number(c['whole_ablation_elapsed_seconds'], 3)} s",
                "1 execução por modelo",
                "Inclui cache/download/carga/indexação/consultas; não é "
                "latência isolada nem comparação justa de velocidade.",
            ]
        )
    for what in (
        "Embedding de consulta em CPU",
        "Retrieval isolado em CPU",
        "Pesos integrais FP16 em T4 16 GB",
    ):
        rows.append(
            [
                what,
                "Lacuna de medição",
                "Não executado; limpo/contaminado não se aplica",
                "0 medições isoladas",
                "Pendente; sem valor estimado",
                "0 benchmarks novos nesta consolidação",
                "Não inferir tempo pela diferença pipeline menos geração "
                "nem confundir compute FP16 com pesos FP16.",
            ]
        )
    table(
        "08-custo",
        "Qual custo computacional e latência foram medidos, em qual hardware?",
        rows,
        [CPATH],
    )

    primary = find_pair(
        retrieval,
        "methods",
        reference="english",
        variant="multilingual",
        policy="ranking",
        mode="sem_filtro",
        k=5,
        metric="recall_capped_at_k",
    )
    g = generation["experiments"]
    rowmap = {(h["experiment"], h["question_id"]): h for h in humans}
    rows = [
        [
            "D versus C",
            "Ganho da correção por chamada adicional",
            exposure("D"),
            "27 saídas; 25 correções novas",
            f"C={fraction(g['C']['accepted'])}; D={fraction(g['D']['accepted'])}; sem ganho",
            f"{correction['corrections_accepted']}/{correction['corrections_requested']} "
            f"recuperadas; 25 chamadas extras",
            "Resultado neste conjunto contaminado não prova que todo "
            "retry seja inútil em outros contratos.",
        ],
        [
            "Texto livre",
            "Melhor aceitação estrita observada em C/D",
            exposure("C"),
            "27 saídas por experimento",
            f"v1={fraction(g['v1']['accepted'])}; C/D={fraction(g['C']['accepted'])}",
            f"C rejeitou "
            f"{g['C']['accepted']['applicable'] - g['C']['accepted']['passed']}/27; "
            f"D herdou as duas aceitas",
            "Aceitação estrita não equivale a erro factual nem é "
            "comparação controlada com coortes JSON diferentes.",
        ],
        [
            "Hipótese primária do embedding",
            "Recall limitado@5 sem filtros",
            EXPOSED,
            "24 respondíveis",
            f"delta multilíngue-inglês={number(primary['mean_delta'], 6)}",
            f"V/E/D={primary['wins']}/{primary['ties']}/{primary['losses']}",
            LIMIT,
        ],
    ]
    for key, title in [
        (("v3-new", "n12"), "Trecho literal não implica sustentação"),
        (("C", "q23"), "Resposta irrelevante aceita"),
        (("json-v1", "n09"), "Fato inventado com ID válido"),
        (("v3-new", "n14"), "Conteúdo sustentado bloqueado por transcrição"),
    ]:
        h = rowmap[key]
        diag = g[key[0]]["diagnostics"][key[1]]
        rows.append(
            [
                f"{key[0]}/{key[1]}",
                title,
                exposure(key[0]) + "; caso selecionado",
                "1 caso lido",
                f"parser aceitou={diag['parser_accepted']}; "
                f"humana={h['support']}; responde={h['answers_question']}",
                "1/1 caso observado; " + h["notes"],
                "Exemplo confirmado em leitura assistida; não é prevalência global da falha.",
            ]
        )
    increment = find_pair(
        retrieval,
        "k_increments",
        method="multilingual",
        mode="restaurante",
        policy="ranking",
        from_k=8,
        to_k=12,
    )
    rows.append(
        [
            "k=8→12; multilíngue filtrado",
            "Ruído adicional com k maior",
            EXPOSED,
            "24 respondíveis",
            "Hit não aumenta; recall clássico aumenta",
            f"{integer(increment['additional_relevant'])} relevantes e "
            f"{integer(increment['additional_irrelevant'])} irrelevantes "
            f"adicionais",
            "O custo para a geração não foi isolado; não escolher k "
            "ótimo apenas por estes números.",
        ]
    )
    rows.append(
        [
            "v3 nova: JSON puro",
            "Aderência sem ignorar sufixo",
            exposure("v3-new"),
            f"{g['v3-new']['llm_outputs']} saídas",
            "Primeiro objeto pode ser válido mesmo com sufixo",
            f"schema {fraction(g['v3-new']['schema'])}; sufixos "
            f"ignorados "
            f"{g['v3-new']['ignored_suffix']}/{g['v3-new']['llm_outputs']}; "
            f"JSON sem sufixo 0/{g['v3-new']['llm_outputs']}",
            "A regra de primeiro objeto foi pré-definida e preserva o "
            "bruto; isso não demonstra JSON puro.",
        ]
    )
    table(
        "09-resultados-negativos",
        "O que foi tentado e não sustentou a conclusão esperada?",
        rows,
        [RPATH, GPATH, HPATH, "reports/generation-kaggle-D/analysis.json"],
    )
    return tables, {
        "primary": primary,
        "generation": generation,
        "humans": humans,
        "cost": cost,
        "ai": ai,
        "correction": correction,
    }


def prose(context: dict) -> str:
    pair = context["primary"]
    g = context["generation"]["experiments"]
    humans = context["humans"]
    v1 = context["cost"]["gpu_cohorts"]["v1"]
    correction = context["correction"]
    selected = sum(h["support"] == "sustentada" for h in humans)
    partial = sum(h["support"] == "parcial" for h in humans)
    unsupported = sum(h["support"] == "sem_suporte" for h in humans)
    english = sum(p["reference"] for p in pair["per_question"]) / pair["questions"]
    multilingual = sum(p["variant"] for p in pair["per_question"]) / pair["questions"]
    substantive = {
        q
        for q, d in g["v3-new"]["diagnostics"].items()
        if d["parser_accepted"] and d.get("abstained") is False
    }
    factual = sum(
        r["question_id"] in substantive
        and r["support"] == "sustentada"
        and r["answers_question"] == "sim"
        for r in context["ai"]
        if r["experiment"] == "v3-new"
    )
    return f"""## Resultados e limitações

A hipótese primária de retrieval não se confirmou: sem filtros, recall limitado@5
foi {number(multilingual)} no MiniLM multilíngue contra {number(english)} no inglês,
com {pair["wins"]} vitórias, {pair["ties"]} empates e {pair["losses"]} derrotas nas
{pair["questions"]} respondíveis. O multilíngue teve MRR maior, mas não venceu
palavras-chave em toda métrica. Filtrar restaurante fornece escopo e melhora o
resultado; isso, sozinho, não demonstra melhor entendimento semântico.

C e D aceitaram {fraction(g["C"]["accepted"])} saídas; D acrescentou
{correction["corrections_requested"]} chamadas e recuperou
{correction["corrections_accepted"]} rejeições. O retry foi descartado.
Na v3 com perguntas então novas, {fraction(g["v3-new"]["schema"])} primeiros objetos
passaram o schema (todos com sufixo) e {fraction(g["v3-new"]["accepted"])} passaram o
parser, incluindo duas abstenções do modelo. Havia evidência nas sete respondíveis,
mas apenas {factual}/{len(substantive)} respostas substantivas aceitas eram sustentadas
e pertinentes na leitura de IA. n12 passou ID/trecho e falhou no conteúdo; n14 teve
núcleo factual apoiado, mas foi bloqueada por transcrição. Geração fiel é o gargalo
observado, com custo adicional da validação estrita.

João leu {len(humans)} casos selecionados com auxílio no enquadramento:
{selected} sustentados, {partial} parciais e {unsupported} sem suporte. A revisão é
assistida, não cega, e não estima acurácia global nem valida um juiz LLM independente.
As 30 originais e n01–n10 são expostas; n11–n20 só eram limpas quanto a ajuste prévio
na execução congelada, com corpus conhecido e rótulos de IA. São resultados
descritivos de amostras pequenas, sem significância ou generalização demonstrada;
as mudanças conjuntas não isolam causalmente o efeito do JSON.

No Kaggle/Tesla T4 com NF4, a v1 teve mediana de geração de
{number(v1["generation_seconds"]["median"], 2)} s, carga de
{number(v1["load_seconds_distinct_attributes"][0], 2)} s e pico alocado de
{number(v1["vram_peak_allocated"]["GB"], 2)} GB. Esses tempos não pertencem ao PC local;
carga não se soma por pergunta e reservado difere de alocado. Latências isoladas
de CPU, pesos integrais FP16 e custo monetário seguem pendentes. Nenhuma nova
inferência foi feita para gerar estas tabelas.

[Tabelas, contagens e proveniência](reports/final-results-v1/RESULTADOS.md).
"""


def escape(value) -> str:
    return str(value).replace("|", r"\|").replace("\n", "<br>")


def render_table(table: dict, commit: str, generator_hash: str) -> str:
    lines = [
        f"# {table['question']}",
        "",
        "| " + " | ".join(table["columns"]) + " |",
        "| " + " | ".join("---" for _ in table["columns"]) + " |",
    ]
    lines += ["| " + " | ".join(escape(value) for value in row) + " |" for row in table["rows"]]
    lines += [
        "",
        f"Commit dos arquivos de entrada: `{commit}`.",
        "Gerador: `scripts/build_results.py`; SHA256 LF `" + generator_hash + "`.",
        "Entradas desta tabela:",
        "",
    ]
    if RPATH in table["inputs"]:
        lines.insert(
            -2,
            "R/I somam documentos por pergunta, não IDs únicos no corpus. "
            "Aleatório: 24 perguntas x 200 repetições; contagens em 4.800 pares "
            "pergunta-seed, que não são amostras independentes.",
        )
    for path in table["inputs"]:
        url = f"https://github.com/JoaoNordemann/partner-copilot/blob/{commit}/{path}"
        lines.append(f"- [{path}]({url})")
    return "\n".join(lines) + "\n"


def replace_section(text: str, section: str) -> str:
    if (BEGIN in text) != (END in text):
        raise ValueError("Incomplete generated README markers")
    block = BEGIN + "\n" + section.rstrip() + "\n" + END
    if BEGIN in text:
        if text.count(BEGIN) != 1 or text.count(END) != 1:
            raise ValueError("Duplicate README markers")
        start = text.index(BEGIN)
        end = text.index(END, start) + len(END)
        return text[:start] + block + text[end:]
    return text.rstrip() + "\n\n" + block + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/final-results-v1")
    parser.add_argument("--source-commit", default=INPUT_COMMIT)
    parser.add_argument(
        "--check", action="store_true", help="Check all generated files without writing"
    )
    parser.add_argument("--update-readme", action="store_true")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.parent != (ROOT / "reports").resolve():
        parser.error("Choose a direct child of reports/ as output directory")
    registry = Inputs(ROOT, args.source_commit)
    tables, context = build_tables(registry)
    generator_hash = sha(normalized(Path(__file__).read_bytes()))
    rendered = {
        table["id"] + ".md": render_table(table, args.source_commit, generator_hash)
        for table in tables
    }
    section = prose(context)
    rendered["README-results.md"] = section.replace(
        "(reports/final-results-v1/RESULTADOS.md)", "(RESULTADOS.md)"
    )
    intro = "# Resultados e limitações: documento final\n\n"
    intro += "Consolidação de artefatos existentes, sem modelos, downloads ou novas avaliações.\n"
    intro += (
        "Cada pergunta de pesquisa tem tabela própria, contagens, "
        "exposição e limitação explícitas.\n"
    )
    intro += (
        "Os números são descritivos: não há teste estatístico ou "
        "seleção automática de configuração.\n\n"
    )
    intro += (
        "Reprodução em clone com histórico Git, apenas Python padrão (sem pesos/GPU):\n\n"
        "```powershell\n"
        "python scripts/build_results.py --check --update-readme\n"
        "python scripts/build_results.py --output-dir reports/final-results-reproduced\n"
        "```\n\n"
        "O gerador verifica cada entrada contra o commit fixo e recusa alterações silenciosas.\n"
        "O segundo comando exige diretório novo; --check não escreve arquivos.\n\n"
    )
    rendered["RESULTADOS.md"] = intro + "\n\n".join(rendered[t["id"] + ".md"] for t in tables)
    manifest = {
        "protocol": "final-results-v1",
        "input_commit": args.source_commit,
        "generator": "scripts/build_results.py",
        "generator_sha256_lf": generator_hash,
        "new_inference": False,
        "inputs": registry.files,
        "tables": tables,
        "metric_definitions": {
            "ks": [1, 3, 5, 8, 12],
            "hit": "at least one relevant in top-k",
            "recall_capped": "H / min(k, number relevant)",
            "recall_classic": "H / number relevant",
            "mrr": "1/rank first relevant up to k, else 0",
            "precision": "H/k including empty slots",
            "aggregation": "macro over 24 answerable questions; six negatives separately",
        },
    }
    rendered["manifest.json"] = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    rendered[".gitattributes"] = "* -text whitespace=cr-at-eol\n"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    expected_readme = replace_section(readme, section)
    if args.check:
        for name, content in rendered.items():
            if (output / name).read_text(encoding="utf-8") != content:
                raise ValueError(f"Generated output differs: {name}")
        if args.update_readme and readme != expected_readme:
            raise ValueError("Generated README section differs")
        print(f"Verified {len(tables)} tables, provenance and generated prose.")
        return 0
    output.mkdir(parents=True, exist_ok=False)
    for name, content in rendered.items():
        (output / name).write_text(content, encoding="utf-8")
    if args.update_readme:
        with (ROOT / "README.md").open("w", encoding="utf-8", newline="") as stream:
            stream.write(expected_readme)
    print(f"Saved {len(tables)} tables to {output}; no new inference.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
