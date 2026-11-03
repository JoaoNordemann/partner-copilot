# pipeline.py
from datetime import date

from .generation.prompts import build_prompt
from .schemas import Answer


class RAGPipeline:
    def __init__(self, retriever, llm):
        self.retriever, self.llm = retriever, llm

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
        if not docs:
            return Answer(answer="Sem avaliações relevantes para responder.", sources=[])
        return Answer(
            answer=self.llm.generate(build_prompt(question, docs)),
            sources=[d.review.id for d in docs],
        )
