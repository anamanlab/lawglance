from __future__ import annotations

import time

from immcad_api.providers.error_mapping import map_provider_exception
from immcad_api.providers.base import ProviderError, ProviderResult
from immcad_api.schemas import Citation


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        api_key: str | None,
        *,
        model: str,
        fallback_models: tuple[str, ...] = (),
        timeout_seconds: float,
        max_retries: int,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.fallback_models = fallback_models
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)

    def generate(self, *, message: str, citations: list[Citation], locale: str) -> ProviderResult:
        if not self.api_key:
            raise ProviderError(self.name, "provider_error", "GEMINI_API_KEY not configured")

        try:
            from google import genai
            from google.genai import types
        except Exception as exc:  # pragma: no cover
            raise ProviderError(self.name, "provider_error", f"Gemini SDK unavailable: {exc}") from exc

        # google-genai HttpOptions.timeout is interpreted in milliseconds.
        timeout_millis = max(1000, int(self.timeout_seconds * 1000))
        client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(timeout=timeout_millis),
        )
        prompt = (
            "You are an informational assistant for Canadian immigration law. "
            "Do not provide legal representation advice. "
            f"User locale: {locale}. "
            f"Question: {message.strip()}"
        )

        answer = ""
        last_error: ProviderError | None = None
        models_to_try = [self.model, *self.fallback_models]
        for model_name in models_to_try:
            for attempt in range(self.max_retries + 1):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.2,
                        ),
                    )
                    answer = response.text or ""
                    if answer:
                        break
                    last_error = ProviderError(
                        self.name,
                        "provider_error",
                        f"Empty Gemini response from model '{model_name}'",
                    )
                except Exception as exc:  # pragma: no cover
                    last_error = map_provider_exception(self.name, exc)

                if attempt < self.max_retries:
                    time.sleep(0.4 * (attempt + 1))
                    continue
            if answer:
                break

        if not answer:
            if last_error:
                raise ProviderError(
                    self.name,
                    last_error.code,
                    f"{last_error.message} (models tried: {', '.join(models_to_try)})",
                ) from last_error
            raise ProviderError(self.name, "provider_error", "Empty Gemini response")

        return ProviderResult(
            provider=self.name,
            answer=answer,
            citations=citations,
            confidence="medium",
        )
