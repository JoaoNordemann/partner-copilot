"""Opt-in CUDA tests with real cached Mistral weights; never part of default CI."""

from unittest.mock import Mock

import pytest

from partner_copilot.config import Settings
from partner_copilot.generation.contracts import ABSTENTION_MESSAGE
from partner_copilot.pipeline import RAGPipeline
from partner_copilot.schemas import RetrievedDoc, Review

pytestmark = pytest.mark.gpu


@pytest.fixture(scope="module")
def cached_mistral():
    torch = pytest.importorskip("torch")
    if not torch.cuda.is_available():
        pytest.skip("A CUDA GPU is required for real Mistral inference")
    from partner_copilot.generation import llm

    tokenizer_loader = llm.AutoTokenizer.from_pretrained
    model_loader = llm.AutoModelForCausalLM.from_pretrained

    def cached_tokenizer(*args, **kwargs):
        return tokenizer_loader(*args, **kwargs, local_files_only=True)

    def cached_model(*args, **kwargs):
        return model_loader(*args, **kwargs, local_files_only=True)

    # Keep the actual loaders and model. The wrapper only prohibits network downloads.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(llm.AutoTokenizer, "from_pretrained", cached_tokenizer)
        patch.setattr(llm.AutoModelForCausalLM, "from_pretrained", cached_model)
        yield llm.Mistral4bit(
            settings=Settings(
                _env_file=None,
                llm_model_id="mistralai/Mistral-7B-Instruct-v0.2",
                temperature=0.0,
                generation_seed=42,
                max_new_tokens=128,
            )
        )


@pytest.mark.parametrize(
    "question,should_abstain",
    [
        ("Qual era a cor da fita da caixa?", False),
        ("Qual era o número de série do termômetro?", True),
    ],
)
def test_real_mistral_citation_and_abstention(cached_mistral, question, should_abstain):
    retriever = Mock()
    retriever.retrieve.return_value = [
        RetrievedDoc(
            review=Review(
                id="gpu_fonte_a",
                restaurant_id="rest_gpu",
                text="A caixa estava fechada com fita azul.",
                rating=4,
                created_at="2026-01-15",
                category="teste",
                bairro="Teste",
            ),
            score=0.9,
        )
    ]
    answer = RAGPipeline(retriever, cached_mistral, settings=cached_mistral.settings).ask(
        question, "rest_gpu"
    )
    assert answer.metadata.llm_called and answer.metadata.generation is not None
    assert answer.metadata.generation.vram_peak_allocated_bytes
    if should_abstain:
        assert answer.abstained and answer.abstention_reason == "llm_insufficient_evidence"
        assert answer.answer == ABSTENTION_MESSAGE and answer.sources == []
    else:
        assert not answer.abstained and answer.sources == ["gpu_fonte_a"]
        assert "azul" in answer.answer.casefold()
    print(answer.model_dump_json(indent=2))
