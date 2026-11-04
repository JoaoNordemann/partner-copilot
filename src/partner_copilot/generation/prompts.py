"""Frozen user-message templates and escaped, explicitly untrusted review context."""

import hashlib
import json
import re
from collections.abc import Sequence
from importlib.resources import files

from partner_copilot.generation.contracts import DEFAULT_PROMPT_VERSION, GenerationContractError
from partner_copilot.schemas import RetrievedDoc


def load_prompt_template(version: str = DEFAULT_PROMPT_VERSION) -> str:
    root = files("partner_copilot.generation").joinpath("templates")
    manifest = json.loads(root.joinpath("manifest.json").read_text(encoding="utf-8"))
    entry = manifest["active_versions"].get(version)
    if entry is None:
        raise GenerationContractError(f"Unknown prompt version: {version}")
    template = root.joinpath(entry["file"]).read_text(encoding="utf-8")
    if hashlib.sha256(template.encode("utf-8")).hexdigest() != entry["sha256"]:
        raise GenerationContractError("Prompt hash differs; register a new version before use")
    return template


def _untrusted_json(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    # No literal boundary tags or Mistral chat markers can be introduced by data.
    # Inputs are a scalar string or a dict of scalar values, never structural arrays.
    for char in "<>&[]":
        encoded = encoded.replace(char, f"\\u{ord(char):04x}")
    return encoded


def build_prompt(
    question: str,
    docs: Sequence[RetrievedDoc],
    *,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
) -> str:
    if not question.strip():
        raise GenerationContractError("Question must not be blank")
    records = []
    for doc in docs:
        review = doc.review
        if not re.fullmatch(r"[A-Za-z0-9_-]+", review.id):
            raise GenerationContractError("Review ID cannot be represented as a citation")
        records.append(
            _untrusted_json(
                {
                    "review_id": review.id,
                    "restaurant_id": review.restaurant_id,
                    "item": review.item,
                    "created_at": review.created_at.isoformat(),
                    "rating": review.rating,
                    "text": review.text,
                    "chunk_index": doc.chunk_index,
                    "chunk_count": doc.chunk_count,
                }
            )
        )
    return load_prompt_template(prompt_version).format(
        context="\n".join(records), question=_untrusted_json(question)
    )
