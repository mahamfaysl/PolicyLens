"""Thin Gemini wrapper: structured output, timeouts, retries, and model fallback."""
import logging
import random
import threading
import time
from typing import Optional, Sequence, Tuple, Type, TypeVar

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

log = logging.getLogger("policylens.llm")
T = TypeVar("T", bound=BaseModel)

_RETRYABLE = {408, 429, 500, 502, 503, 504}


class LLMError(RuntimeError):
    """All models failed; the message lists why."""


class AuthError(LLMError):
    """The API key is missing, invalid, or not permitted."""


class GeminiClient:
    def __init__(self, api_key: str, models: Sequence[str], timeout_s: int = 90, retries: int = 2):
        if not api_key:
            raise AuthError("Missing Gemini API key. Set GEMINI_API_KEY in Streamlit secrets or .env.")
        self._client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=timeout_s * 1000)
        )
        self._models = list(models)
        self._retries = retries
        self._unavailable = set()  # models that returned 404 this session
        self._thinking = True  # disabled automatically if a model rejects the setting
        self._lock = threading.Lock()

    def generate(self, prompt: str, schema: Type[T]) -> Tuple[T, str]:
        """Return (parsed result, model used). Raises LLMError with every failure listed."""
        failures = []
        for model in self._models:
            if model in self._unavailable:
                continue
            for attempt in range(self._retries + 1):
                try:
                    return self._call(model, prompt, schema), model
                except errors.APIError as e:
                    code = getattr(e, "code", None)
                    if code in (401, 403):
                        raise AuthError(f"Gemini rejected the API key ({code}): {e}") from e
                    if code == 404:
                        self._unavailable.add(model)
                        failures.append(f"{model}: not available")
                        break
                    if code == 400 and self._thinking and "think" in str(e).lower():
                        self._thinking = False  # retry immediately without the thinking option
                        continue
                    failures.append(f"{model}: {code} {getattr(e, 'message', e)}")
                    if code not in _RETRYABLE:
                        break
                except (ValidationError, ValueError) as e:
                    failures.append(f"{model}: unparseable output ({e.__class__.__name__})")
                except Exception as e:  # network errors, timeouts
                    failures.append(f"{model}: {e.__class__.__name__}: {e}")
                if attempt < self._retries:
                    time.sleep(1.5 * 2**attempt + random.random())
            log.warning("model %s failed, trying next", model)
        raise LLMError("All models failed. " + " | ".join(failures[-6:]))

    def _call(self, model: str, prompt: str, schema: Type[T]) -> T:
        config = {
            "response_mime_type": "application/json",
            "response_schema": schema,
            "temperature": 0.1,
        }
        if self._thinking:
            config["thinking_config"] = types.ThinkingConfig(thinking_level="minimal")
        response = self._client.models.generate_content(model=model, contents=prompt, config=config)
        parsed: Optional[T] = response.parsed if isinstance(response.parsed, schema) else None
        if parsed is None:
            parsed = schema.model_validate_json(response.text)
        return parsed
