"""Independent, hash-checked parser versions; v1 remains the default."""

import hashlib
import json
from collections.abc import Sequence
from importlib.resources import files

from partner_copilot.generation.contracts import DEFAULT_PARSER_VERSION, GenerationContractError
from partner_copilot.generation.output_v1 import ParsedGeneration
from partner_copilot.schemas import RetrievedDoc


def parser_identity(version: str = DEFAULT_PARSER_VERSION) -> dict[str, str]:
    root = files("partner_copilot.generation")
    manifest = json.loads(
        root.joinpath("templates/parser-manifest.json").read_text(encoding="utf-8")
    )
    entry = manifest["active_versions"].get(version)
    if entry is None:
        raise GenerationContractError(f"Unknown parser version: {version}")
    for name, expected in entry["files"].items():
        source = root.joinpath(name).read_text(encoding="utf-8")
        if hashlib.sha256(source.encode("utf-8")).hexdigest() != expected:
            raise GenerationContractError("Parser hash differs; register a new version before use")
    digest = hashlib.sha256(json.dumps(entry["files"], sort_keys=True).encode()).hexdigest()
    return {"parser_version": version, "parser_sha256": digest}


def parse_generation(
    text: str, docs: Sequence[RetrievedDoc], *, parser_version: str = DEFAULT_PARSER_VERSION
) -> ParsedGeneration:
    parser_identity(parser_version)
    if parser_version == "parser-v1":
        from partner_copilot.generation.output_v1 import parse_generation as parse
    elif parser_version == "parser-v2":
        from partner_copilot.generation.output_v2 import parse_generation as parse
    else:
        from partner_copilot.generation.output_json_v1 import parse_generation as parse
    return parse(text, docs)
