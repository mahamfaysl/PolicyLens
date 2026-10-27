"""Runtime settings, overridable through environment variables (or .env)."""
import os
from dataclasses import dataclass

# Fastest first; later entries are only used if earlier ones fail or are unavailable.
DEFAULT_MODELS = (
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
)


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    models: tuple = DEFAULT_MODELS
    # Documents up to this many characters (~35k tokens) are analysed in one call.
    single_pass_chars: int = 150_000
    # Larger documents are split into page-aligned chunks of about this size.
    chunk_chars: int = 60_000
    max_workers: int = 8
    timeout_s: int = 90
    retries: int = 2
    max_pages: int = 2000

    @classmethod
    def from_env(cls) -> "Settings":
        models = tuple(m.strip() for m in os.getenv("PL_MODELS", "").split(",") if m.strip())
        return cls(
            models=models or DEFAULT_MODELS,
            single_pass_chars=_int("PL_SINGLE_PASS_CHARS", cls.single_pass_chars),
            chunk_chars=_int("PL_CHUNK_CHARS", cls.chunk_chars),
            max_workers=_int("PL_MAX_WORKERS", cls.max_workers),
            timeout_s=_int("PL_TIMEOUT_S", cls.timeout_s),
            retries=_int("PL_RETRIES", cls.retries),
            max_pages=_int("PL_MAX_PAGES", cls.max_pages),
        )
