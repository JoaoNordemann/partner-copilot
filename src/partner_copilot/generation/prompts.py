# generation/prompts.py
RAG_PROMPT = """Você é um analista de operações para restaurantes parceiros de delivery.
Responda APENAS com base nas avaliações abaixo.
Se não houver evidência suficiente, diga que não há dados.
Cite as avaliações usando [id]. Termine com 2-3 ações concretas (cardápio, embalagem, operação).

AVALIAÇÕES:
{context}

PERGUNTA: {question}
"""


def build_prompt(question, docs):
    ctx = "\n".join(
        f"[{d.review.id}] (nota {d.review.rating}, item: {d.review.item}) {d.review.text}"
        for d in docs
    )
    return RAG_PROMPT.format(context=ctx, question=question)
