# pipeline.py
from .generation.prompts import build_prompt
from .schemas import Answer


class RAGPipeline:
    def __init__(self, retriever, llm):
        self.retriever, self.llm = retriever, llm

    def ask(self, question: str, restaurant_id: str, aspect: str | None = None) -> Answer:
        docs = self.retriever.retrieve(question, restaurant_id, aspect)
        if not docs:
            return Answer(answer="Sem avaliações relevantes para responder.", sources=[])
        return Answer(
            answer=self.llm.generate(build_prompt(question, docs)),
            sources=[d.review.id for d in docs],
        )
