"""Evidence-grounded generation with typed answers and explicit abstention paths."""

import logging
from datetime import date
from time import perf_counter

from partner_copilot.config import Settings, get_settings
from partner_copilot.generation.contracts import (
    ABSTENTION_MESSAGE,
    LLM,
    InvalidCitationError,
    MeasuredLLM,
)
from partner_copilot.generation.output import parse_generation
from partner_copilot.generation.prompts import build_prompt, load_prompt_template
from partner_copilot.generation.provider import get_llm
from partner_copilot.retrieval.retriever import Retriever
from partner_copilot.schemas import Answer, AnswerMetadata

logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(
        self, retriever: Retriever, llm: LLM | None = None, *, settings: Settings | None = None
    ) -> None:
        self.retriever, self.llm = retriever, llm
        self.settings = settings if settings is not None else get_settings()
        load_prompt_template(self.settings.prompt_version)

    def ask(
        self,
        question: str,
        restaurant_id: str,
        aspect: str | None = None,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        item: str | None = None,
        category: str | None = None,
        city: str | None = None,
        bairro: str | None = None,
    ) -> Answer:
        started = perf_counter()
        docs = self.retriever.retrieve(
            question,
            restaurant_id,
            aspect,
            start_date=start_date,
            end_date=end_date,
            item=item,
            category=category,
            city=city,
            bairro=bairro,
        )
        context = docs[: self.settings.context_k]
        generation_metrics = None
        if not docs:
            text, sources, abstained, reason = ABSTENTION_MESSAGE, [], True, "retriever_empty"
        else:
            prompt = build_prompt(question, context, prompt_version=self.settings.prompt_version)
            llm = self.llm if self.llm is not None else get_llm(self.settings)
            if isinstance(llm, MeasuredLLM):
                generated = llm.generate_with_metrics(prompt)
                generation_metrics = generated.metrics
                generated_text = generated.text
            else:
                generated_text = llm.generate(prompt)
            try:
                parsed = parse_generation(generated_text, context)
            except InvalidCitationError as exc:
                logger.warning(
                    "generation_rejected code=%s invalid_citation_count=%d",
                    exc.code,
                    exc.invalid_citation_count,
                )
                raise
            text, sources, abstained = parsed.answer, parsed.sources, parsed.abstained
            reason = "llm_insufficient_evidence" if abstained else None
        result = Answer(
            answer=text,
            sources=sources,
            abstained=abstained,
            abstention_reason=reason,
            metadata=AnswerMetadata(
                latency_ms=0,
                retrieved_documents=len(docs),
                context_documents=len(context),
                prompt_version=self.settings.prompt_version,
                llm_called=bool(docs),
                generation=generation_metrics,
            ),
        )
        # End timing after output parsing and Pydantic validation, before returning.
        result.metadata.latency_ms = (perf_counter() - started) * 1000
        return result
