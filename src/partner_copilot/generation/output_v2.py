"""Parser v2: normalize escaped underscores, then enforce the frozen v1 contract."""

from collections.abc import Sequence

from partner_copilot.generation.output_v1 import ParsedGeneration
from partner_copilot.generation.output_v1 import parse_generation as parse_v1
from partner_copilot.schemas import RetrievedDoc


def parse_generation(text: str, docs: Sequence[RetrievedDoc]) -> ParsedGeneration:
    if isinstance(text, str):
        text = text.replace(r"\_", "_")
    return parse_v1(text, docs)
