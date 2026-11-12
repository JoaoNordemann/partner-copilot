"""Summarize the journaled T4 run using medians, maxima and sample counts."""

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import median


def records(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def stats(values):
    return {"n": len(values), "median": median(values), "max": max(values)} if values else {"n": 0}


def report(folder):
    result = {"session": records(folder / "session.jsonl"), "precision": {}, "pairs": {}}
    by_mode = {}
    for mode in ("nf4", "fp16"):
        rows = records(folder / f"{mode}.jsonl")
        summary = {r["event"]: r for r in rows if r["event"] in ("environment", "load", "oom")}
        summary["cohorts"] = {}
        by_mode[mode] = {}
        for group, expected in (("limpo_original", 9), ("contaminado", 27)):
            by_id = {r["id"]: r for r in rows if r["event"] == "generation" and r["group"] == group}
            by_mode[mode][group] = by_id
            selected = list(by_id.values())
            summary["cohorts"][group] = {
                "expected": expected,
                "accepted": sum(row["accepted"] for row in selected),
                "latency_seconds": stats([row["seconds"] for row in selected]),
                "tokens_per_second": stats(
                    [r["generated_tokens"] / r["generation_seconds"] for r in selected]
                ),
                "peak_allocated_bytes": max(
                    (r["memory"]["peak_allocated_bytes"] for r in selected), default=None
                ),
                "peak_reserved_bytes": max(
                    (r["memory"]["peak_reserved_bytes"] for r in selected), default=None
                ),
            }
        result["precision"][mode] = summary

    for group, nf4 in by_mode["nf4"].items():
        fp16 = by_mode["fp16"][group]
        paired = sorted(nf4.keys() & fp16.keys())
        both_accepted = [i for i in paired if nf4[i]["accepted"] and fp16[i]["accepted"]]
        result["pairs"][group] = {
            "n": len(paired),
            "both_accepted": len(both_accepted),
            "raw_changed_ids": [i for i in paired if nf4[i]["raw"] != fp16[i]["raw"]],
            "acceptance_changed_ids": [
                i for i in paired if nf4[i]["accepted"] != fp16[i]["accepted"]
            ],
            "structured_changed_ids": [
                i for i in both_accepted if nf4[i]["structured"] != fp16[i]["structured"]
            ],
        }

    server_records = {}
    path = folder / "api-server.log"
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith('{"event": "request_completed"'):
                row = json.loads(line)
                server_records[row["request_id"]] = row

    def times(row):
        response = row.get("response", {})
        metadata = response.get("metadata", {})
        server = server_records.get(response.get("request_id") or metadata.get("request_id"), {})
        timing = metadata.get("timings_ms") or server.get("timings_ms") or {}
        if timing.get("generation_ms") and timing.get("queue_ms") is not None:
            return {
                **timing,
                "generation_without_queue_ms": max(0, timing["generation_ms"] - timing["queue_ms"]),
            }
        return timing

    api = [r for r in records(folder / "api.jsonl") if r["event"] == "http"]
    sequential = [r for r in api if r["group"] == "sequential"]
    ok = [r for r in sequential if r.get("http_status") == 200]
    concurrent = [r for r in api if r["group"] == "concurrent"]
    result["api"] = {
        "sequential_status": dict(
            Counter(str(r.get("http_status", "client_error")) for r in sequential)
        ),
        "http_seconds": stats([r["seconds"] for r in sequential]),
        "http_success_seconds": stats([r["seconds"] for r in ok]),
        "stages_ms": {
            stage: stats(
                [
                    x[stage]
                    for row in sequential
                    if (stage != "validation_ms" or row.get("http_status") == 200)
                    and (x := times(row)).get(stage) is not None
                ]
            )
            for stage in (
                "embedding_ms",
                "search_ms",
                "queue_ms",
                "generation_without_queue_ms",
                "validation_ms",
            )
        },
        "concurrent": [
            {
                "id": r["id"],
                "seconds": r["seconds"],
                "http_status": r.get("http_status"),
                "timings_ms": times(r),
            }
            for r in concurrent
        ],
        "generation_intervals": records(folder / "api-generation-intervals.jsonl"),
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    print(json.dumps(report(args.folder), indent=2, ensure_ascii=False))
