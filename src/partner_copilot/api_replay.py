"""Explicitly approved v3 recordings; never searches for a similar question."""

import hashlib
import json
from pathlib import Path

from partner_copilot.api_models import APIError, AskRequest
from partner_copilot.generation.output import parse_generation, parser_identity
from partner_copilot.generation.output_v3 import decode_output
from partner_copilot.generation.prompts import load_prompt_template
from partner_copilot.schemas import RetrievedDoc, Review

PROFILE_FIELDS = (
    "prompt_version",
    "parser_version",
    "context_k",
    "retrieval_min_score",
    "max_new_tokens",
    "temperature",
    "generation_seed",
    "embedding_model",
    "embedding_prefix_mode",
    "llm_model_id",
)


def request_key(request: AskRequest) -> str:
    return json.dumps(
        {
            "restaurant_id": request.restaurant_id,
            "question": request.question,
            "filters": request.filter_values(),
            "k": request.k,
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


class ReplayCatalog:
    def __init__(self, path: Path, settings):
        self.entries = {}
        catalogue = json.loads(path.read_text(encoding="utf-8"))
        if catalogue.get("schema_version") != "replay-catalog-v1":
            raise APIError(503, "replay_unavailable")
        root = path.parent
        for entry in catalogue["entries"]:
            source_path = (root / entry["source_file"]).resolve()
            data = source_path.read_bytes()
            if hashlib.sha256(data).hexdigest() != entry["source_sha256"]:
                raise APIError(409, "replay_snapshot_mismatch")
            matches = [
                r
                for r in map(json.loads, data.decode("utf-8").splitlines())
                if r["question_id"] == entry["question_id"]
            ]
            if len(matches) != 1:
                raise APIError(503, "replay_unavailable")
            row = matches[0]
            if (
                row.get("cohort") not in ("new", "contaminated")
                or row.get("backend") != "real_mistral_nf4"
            ):
                raise APIError(503, "replay_unavailable")
            if row["question_id"] in {f"n{i:02}" for i in range(21, 31)}:
                raise APIError(503, "replay_unavailable")
            expected_prompt = hashlib.sha256(
                load_prompt_template(settings.prompt_version).encode()
            ).hexdigest()
            if (
                row.get("prompt_sha256") != expected_prompt
                or row.get("parser_sha256")
                != parser_identity(settings.parser_version)["parser_sha256"]
            ):
                raise APIError(409, "replay_snapshot_mismatch")
            profile = row["settings"]
            if any(profile.get(k) != getattr(settings, k) for k in PROFILE_FIELDS):
                raise APIError(409, "replay_snapshot_mismatch")
            proof = (root / entry["approval_file"]).read_bytes()
            if hashlib.sha256(proof).hexdigest() != entry["approval_sha256"]:
                raise APIError(409, "replay_snapshot_mismatch")
            experiment = "v3-new" if row["cohort"] == "new" else "v3-old"
            approvals = [
                r
                for r in map(json.loads, proof.decode("utf-8").splitlines())
                if r.get("question_id") == row["question_id"]
                and r.get("experiment") == experiment
                and r.get("status") == "completed"
                and r.get("origin") == "human"
                and r.get("support") == "sustentada"
                and r.get("answers_question") == "sim"
            ]
            if len(approvals) != 1 or row.get("error") or row.get("answer") is None:
                raise APIError(503, "replay_unavailable")
            request = AskRequest(
                restaurant_id=row["filtros"]["restaurant_id"],
                question=row["pergunta"],
                filters={k: v for k, v in row["filtros"].items() if k != "restaurant_id"},
                k=profile["retrieval_k"],
            )
            corpus_path = (root / entry["corpus_file"]).resolve()
            corpus_bytes = corpus_path.read_bytes()
            if hashlib.sha256(corpus_bytes).hexdigest() != entry["corpus_sha256"]:
                raise APIError(409, "replay_snapshot_mismatch")
            recorded_hash = row["snapshot_sha256_lf"].get("corpus") or row[
                "snapshot_sha256_lf"
            ].get("corpus.jsonl")
            actual_hash = hashlib.sha256(
                corpus_bytes.decode("utf-8").replace("\r\n", "\n").encode()
            ).hexdigest()
            if recorded_hash != actual_hash:
                raise APIError(409, "replay_snapshot_mismatch")
            corpus = {
                r.id: r
                for r in (
                    Review.model_validate_json(line)
                    for line in corpus_bytes.decode("utf-8").splitlines()
                )
            }
            docs = []
            for d in row["context"]:
                review = corpus[d["review_id"]]
                if review.text != d["text"] or review.restaurant_id != request.restaurant_id:
                    raise APIError(409, "replay_snapshot_mismatch")
                if request.filters.item and review.item != request.filters.item:
                    raise APIError(409, "replay_snapshot_mismatch")
                f = request.filters
                if (
                    (f.start_date and review.created_at < f.start_date)
                    or (f.end_date and review.created_at > f.end_date)
                    or (f.aspect and review.aspects.get(f.aspect) != "neg")
                ):
                    raise APIError(409, "replay_snapshot_mismatch")
                docs.append(RetrievedDoc(review=review, score=d["score"]))
            raw = row["raw_response"] if row["llm_called"] else '{"abstem":true,"afirmacoes":[]}'
            # Revalidate the saved output against its own corpus, never production RAG.
            parsed = parse_generation(raw, docs, parser_version="parser-v3")
            if (
                parsed.answer != row["answer"]["answer"]
                or parsed.sources != row["answer"]["sources"]
                or parsed.abstained != row["answer"]["abstained"]
            ):
                raise APIError(409, "replay_snapshot_mismatch")
            result = decode_output(raw).value
            if request_key(request) in self.entries:
                raise APIError(503, "replay_unavailable")
            self.entries[request_key(request)] = {
                "raw": raw,
                "docs": docs,
                "result": result,
                "retrieved_count": len(row["retrieved"]),
                "reason": row["answer"]["abstention_reason"],
                "source_run": {
                    "experiment_id": row["experiment_id"],
                    "question_id": row["question_id"],
                    "source_sha256": entry["source_sha256"],
                    "corpus_sha256": entry["corpus_sha256"],
                    "corpus": "recorded_eval_snapshot",
                    "source_commit": row["environment"]["source_commit"],
                    "recorded_at_utc": row.get("recorded_at_utc"),
                    "environment": {
                        k: v
                        for k, v in row["environment"].items()
                        if k
                        in {
                            "python",
                            "packages",
                            "gpu_names",
                            "torch_cuda_version",
                            "source_commit",
                            "source_code_sha256",
                        }
                    },
                    "llm_called": row["llm_called"],
                    "prompt_version": row["prompt_version"]
                    if "prompt_version" in row
                    else profile["prompt_version"],
                    "parser_version": profile["parser_version"],
                    "approval": {
                        "reviewer": approvals[0]["reviewer"],
                        "origin": "human_assisted",
                        "method": approvals[0].get("method"),
                    },
                    "historical_metrics": row.get("generation_metrics"),
                },
                "restaurant_id": request.restaurant_id,
                "item": request.filters.item,
            }
        if not self.entries:
            raise APIError(503, "replay_unavailable")

    def lookup(self, request: AskRequest) -> dict:
        try:
            return self.entries[request_key(request)]
        except KeyError as exc:
            raise APIError(404, "replay_not_found") from exc

    def restaurants(self) -> list[dict]:
        identifiers = sorted({r["restaurant_id"] for r in self.entries.values()})
        return [
            {
                "restaurant_id": identifier,
                "name": identifier,
                "items": sorted(
                    {
                        d.review.item
                        for r in self.entries.values()
                        if r["restaurant_id"] == identifier
                        for d in r["docs"]
                        if d.review.item
                    }
                ),
            }
            for identifier in identifiers
        ]
