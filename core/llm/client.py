from __future__ import annotations

import json
import re
from typing import Any, Literal

from config import settings

_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
_OPENAI_CHAT_MODEL = "gpt-4o"
_OPENAI_EMBED_MODEL = "text-embedding-3-small"
_VOYAGE_MODEL = "voyage-3"

_MARKDOWN_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


class LLMError(Exception):
    """Raised when an LLM call fails."""


class EmbeddingError(Exception):
    """Raised when an embedding call fails."""


class LLMClient:
    def __init__(self) -> None:
        self._anthropic_client: Any | None = None
        self._openai_client: Any | None = None
        self._mode: Literal["anthropic", "openai", "rule_based"]

        if settings.has_anthropic_key:
            import anthropic

            self._anthropic_client = anthropic.Anthropic(
                api_key=settings.ANTHROPIC_API_KEY,
            )
            self._mode = "anthropic"
        elif settings.has_openai_key:
            import openai

            self._openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            self._mode = "openai"
        else:
            self._mode = "rule_based"

    @property
    def mode(self) -> Literal["anthropic", "openai", "rule_based"]:
        return self._mode

    def is_ai_available(self) -> bool:
        return self._mode != "rule_based"

    # ------------------------------------------------------------------
    # Text completion
    # ------------------------------------------------------------------

    def ask(self, system: str, user: str, max_tokens: int = 2000) -> str:
        if self._mode == "anthropic":
            return self._ask_anthropic(system, user, max_tokens)
        if self._mode == "openai":
            return self._ask_openai(system, user, max_tokens)
        raise LLMError(
            "No LLM API key configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
        )

    def _ask_anthropic(self, system: str, user: str, max_tokens: int) -> str:
        try:
            response = self._anthropic_client.messages.create(  # type: ignore[union-attr]
                model=_ANTHROPIC_MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return response.content[0].text  # type: ignore[index]
        except Exception as exc:
            raise LLMError(f"Anthropic API error: {exc}") from exc

    def _ask_openai(self, system: str, user: str, max_tokens: int) -> str:
        try:
            response = self._openai_client.chat.completions.create(  # type: ignore[union-attr]
                model=_OPENAI_CHAT_MODEL,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise LLMError(f"OpenAI API error: {exc}") from exc

    # ------------------------------------------------------------------
    # JSON completion
    # ------------------------------------------------------------------

    def ask_json(
        self, system: str, user: str, schema_hint: str = ""
    ) -> dict[str, Any]:
        full_system = system
        if schema_hint:
            full_system = f"{system}\n\nExpected JSON schema:\n{schema_hint}"

        raw = self.ask(full_system, user)
        text = raw.strip()

        fence_match = _MARKDOWN_FENCE_RE.search(text)
        if fence_match:
            text = fence_match.group(1).strip()

        try:
            return json.loads(text)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            return {"error": "parse_failed", "raw": raw}

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    def embed(self, text: str) -> list[float]:
        if self._mode == "anthropic":
            return self._embed_voyage(text)
        if self._mode == "openai":
            return self._embed_openai(text)
        raise EmbeddingError(
            "No embedding provider available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
        )

    def _embed_voyage(self, text: str) -> list[float]:
        try:
            response = self._anthropic_client.embeddings.create(  # type: ignore[union-attr]
                model=_VOYAGE_MODEL,
                input=[text],
            )
            return list(response.data[0].embedding)  # type: ignore[index]
        except Exception:
            if settings.has_openai_key:
                return self._embed_openai(text)
            raise EmbeddingError(
                "Voyage embedding failed and no OpenAI key available as fallback."
            )

    def _embed_openai(self, text: str) -> list[float]:
        try:
            if self._openai_client is None:
                import openai

                self._openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            response = self._openai_client.embeddings.create(
                model=_OPENAI_EMBED_MODEL,
                input=[text],
            )
            return list(response.data[0].embedding)
        except Exception as exc:
            raise EmbeddingError(f"OpenAI embedding error: {exc}") from exc


llm = LLMClient()
