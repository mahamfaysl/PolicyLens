"""Check LLM-extracted evidence against the source text (no model calls)."""
import re
import unicodedata
from typing import Dict, List, Optional, Set

from pdf_reader import ParsedDocument
from schema import ExtractedIndicator, VerifiedIndicator

_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _squash(text: str) -> str:
    # Spaces removed too, so PDF line-break hyphenation ("moni- toring") still matches.
    return _norm(text).replace(" ", "")


def _numbers(text: str) -> Set[str]:
    return {n.replace(",", "") for n in _NUM.findall(text)}


class Verifier:
    def __init__(self, doc: ParsedDocument):
        self._squashed: Dict[int, str] = {i: _squash(t) for i, t in enumerate(doc.pages, 1)}
        self._tokens: Dict[int, Set[str]] = {i: set(_norm(t).split()) for i, t in enumerate(doc.pages, 1)}
        self._all_numbers = _numbers("\n".join(doc.pages))

    def _find_page(self, squashed_quote: str, exclude: Optional[int]) -> Optional[int]:
        for page, text in self._squashed.items():
            if page != exclude and squashed_quote in text:
                return page
        return None

    def check(self, ind: ExtractedIndicator) -> VerifiedIndicator:
        data = ind.model_dump()
        quote = _squash(ind.evidence_quote or "")
        status = "no_quote"
        page = ind.source_page

        if len(quote) >= 8:
            if page in self._squashed and quote in self._squashed[page]:
                status = "verified"
            else:
                found = self._find_page(quote, page)
                if found:
                    status, page = "page_corrected", found
                else:
                    words = _norm(ind.evidence_quote).split()
                    pool = self._tokens.get(page) or set().union(*self._tokens.values())
                    hit = sum(1 for w in words if w in pool) / max(len(words), 1)
                    status = "partial" if hit >= 0.85 else "unverified"

        values = _numbers(f"{ind.baseline_value or ''} {ind.target_value or ''}")
        numbers_ok = all(v in self._all_numbers for v in values) if values else None

        data.update(source_page=page, verification=status, numbers_in_source=numbers_ok)
        return VerifiedIndicator(**data)

    def check_all(self, indicators: List[ExtractedIndicator]) -> List[VerifiedIndicator]:
        return [self.check(i) for i in indicators]
