"""Deterministic token windows bounded by the embedding model's actual context size."""

from __future__ import annotations

from typing import Any, Protocol


class InvalidChunkInput(ValueError):
    """A record cannot be chunked; distinct from model or configuration failures."""


class TextSplitter(Protocol):
    def split(self, text: str) -> list[str]: ...


class TokenizerProvider(Protocol):
    def document_tokenizer(self) -> tuple[Any, int, str]: ...


class TokenTextSplitter:
    def __init__(
        self,
        provider: TokenizerProvider,
        *,
        overlap_tokens: int = 16,
        max_tokens: int | None = None,
    ) -> None:
        if overlap_tokens < 0 or (max_tokens is not None and max_tokens < 1):
            raise ValueError("Invalid chunk token limit or overlap")
        if max_tokens is not None and max_tokens <= overlap_tokens:
            raise ValueError("Chunk limit must exceed overlap")
        self.provider = provider
        self.overlap_tokens = overlap_tokens
        self.max_tokens = max_tokens
        self._context: tuple[Any, int, int, str] | None = None

    def prepare(self) -> tuple[Any, int, int, str]:
        """Lazily validate the effective budget; reset orchestration can preflight this."""
        if self._context is None:
            tokenizer, model_limit, prefix = self.provider.document_tokenizer()
            limit = (
                min(model_limit, self.max_tokens) if self.max_tokens is not None else model_limit
            )
            prefix_size = len(tokenizer(prefix, add_special_tokens=False)["input_ids"])
            capacity = limit - prefix_size - tokenizer.num_special_tokens_to_add(pair=False)
            if capacity <= self.overlap_tokens:
                raise RuntimeError(
                    "Chunk token budget must exceed overlap after prefixes/special tokens"
                )
            self._context = (tokenizer, limit, capacity, prefix)
        return self._context

    def split(self, text: str) -> list[str]:
        if not text.strip():
            raise InvalidChunkInput("Review text must not be blank")
        tokenizer, limit, capacity, prefix = self.prepare()
        try:
            encoded = tokenizer(
                text,
                add_special_tokens=False,
                return_offsets_mapping=True,
                truncation=False,
                verbose=False,
            )
        except NotImplementedError as exc:
            raise RuntimeError(
                "Token chunking requires a fast tokenizer with character offsets"
            ) from exc
        offsets = encoded["offset_mapping"]
        if not offsets:
            raise InvalidChunkInput("Review has no encodable tokens")

        def length(value: str) -> int:
            return len(
                tokenizer(prefix + value, add_special_tokens=True, truncation=False, verbose=False)[
                    "input_ids"
                ]
            )

        if length(text) <= limit:
            return [text]
        chunks = []
        start = 0
        while start < len(offsets):
            end = min(start + capacity, len(offsets))
            begin_char = 0 if start == 0 else offsets[start][0]
            while end > start:
                end_char = len(text) if end == len(offsets) else offsets[end - 1][1]
                piece = text[begin_char:end_char]
                if piece.strip() and length(piece) <= limit:
                    break
                end -= 1
            if end <= start:
                raise InvalidChunkInput("A token cannot fit into the configured chunk budget")
            chunks.append(piece)
            if end == len(offsets):
                break
            start = max(start + 1, end - self.overlap_tokens)
        return chunks
