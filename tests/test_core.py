import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from config import Settings
from llm import AuthError, GeminiClient, LLMError
from pdf_reader import DocumentError, ParsedDocument, chunk_document, read_pdf
from pipeline import _dedupe_text, _merge_indicators, analyze_document
from report import safe_filename, to_markdown
from schema import ChunkFindings, ExtractedIndicator, InstitutionalAudit, Synthesis
from verify import Verifier

PAGES = [
    "Project overview. The programme monitors annual financing com-\nmitments of at least $50 million.",
    "Readiness level must exceed 80% by 2027. Baseline was 45%.",
]
DOC = ParsedDocument(PAGES)


def ind(**kw):
    base = dict(indicator_name="x", status_or_evidence_gap="gap")
    base.update(kw)
    return ExtractedIndicator(**base)


# --- verification -----------------------------------------------------------
def test_quote_verified_despite_hyphenation():
    v = Verifier(DOC).check(ind(source_page=1, evidence_quote="annual financing commitments of at least $50 million"))
    assert v.verification == "verified"


def test_wrong_page_is_corrected():
    v = Verifier(DOC).check(ind(source_page=1, evidence_quote="Readiness level must exceed 80% by 2027"))
    assert (v.verification, v.source_page) == ("page_corrected", 2)


def test_fabricated_quote_is_unverified():
    v = Verifier(DOC).check(ind(source_page=1, evidence_quote="The ministry doubled the budget in March"))
    assert v.verification == "unverified"


def test_missing_quote_and_number_check():
    assert Verifier(DOC).check(ind()).verification == "no_quote"
    assert Verifier(DOC).check(ind(baseline_value="45%", target_value="80%")).numbers_in_source is True
    assert Verifier(DOC).check(ind(target_value="99%")).numbers_in_source is False
    assert Verifier(DOC).check(ind(target_value="at least three")).numbers_in_source is None


# --- chunking / reading -----------------------------------------------------
def test_chunks_are_page_aligned_and_bounded():
    doc = ParsedDocument(["a" * 400 for _ in range(10)])
    chunks = chunk_document(doc, 1000)
    assert len(chunks) > 1
    assert all(len(c) < 1100 for c in chunks)
    assert chunks[0].startswith("--- PAGE 1 ---")
    assert sum(c.count("--- PAGE") for c in chunks) == 10


def test_oversized_page_is_split():
    chunks = chunk_document(ParsedDocument(["b" * 2500]), 1000)
    assert len(chunks) == 3


def test_read_pdf_rejects_garbage():
    with pytest.raises(DocumentError):
        read_pdf(b"not a pdf")


def test_read_sample_pdf():
    sample = Path(__file__).resolve().parent.parent / "data" / "59047-001-tar-1173551-en.pdf"
    if sample.exists():
        doc = read_pdf(sample.read_bytes())
        assert len(doc.pages) == 15 and doc.characters > 10_000


# --- merging ----------------------------------------------------------------
def test_dedupe_and_merge():
    assert _dedupe_text(["Weak data systems", "weak data systems.", "Procurement delays"], 10) == [
        "Weak data systems",
        "Procurement delays",
    ]
    merged = _merge_indicators([ind(indicator_name="A", target_value="5"), ind(indicator_name="a", target_value="5", evidence_quote="q", source_page=2)])
    assert len(merged) == 1 and merged[0].evidence_quote == "q"


# --- pipeline with a fake model --------------------------------------------
class FakeClient:
    def __init__(self):
        self.calls = []

    def generate(self, prompt, schema):
        self.calls.append(schema)
        if schema is InstitutionalAudit:
            return InstitutionalAudit(**_synth_kwargs(), tracked_indicators=[ind(indicator_name="R", source_page=2, evidence_quote="Readiness level must exceed 80%")]), "fake"
        if schema is ChunkFindings:
            return ChunkFindings(core_objectives=["o"], tracked_indicators=[ind(indicator_name="R", source_page=2, evidence_quote="Readiness level must exceed 80%")], implementation_bottlenecks=["b"]), "fake"
        return Synthesis(**_synth_kwargs()), "fake"


def _synth_kwargs():
    return dict(institution_name="ADB", project_title="P", sector="S", executive_summary="E", core_objectives=["o"],
                implementation_bottlenecks=["b"], stakeholder_briefing_angle="A", tailored_outreach_memo="M")


def _pdf_bytes():
    sample = Path(__file__).resolve().parent.parent / "data" / "59047-001-tar-1173551-en.pdf"
    return sample.read_bytes()


@pytest.mark.skipif(not (Path(__file__).resolve().parent.parent / "data" / "59047-001-tar-1173551-en.pdf").exists(), reason="sample missing")
def test_pipeline_single_and_map_reduce():
    single = FakeClient()
    r1 = analyze_document(_pdf_bytes(), single, "s.pdf", Settings())
    assert r1.meta.mode == "single_pass" and single.calls == [InstitutionalAudit]

    mr = FakeClient()
    r2 = analyze_document(_pdf_bytes(), mr, "s.pdf", Settings(single_pass_chars=1000, chunk_chars=5000))
    assert r2.meta.mode == "map_reduce" and r2.meta.chunks > 1
    assert mr.calls.count(Synthesis) == 1 and len(r2.indicators) == 1  # duplicates across chunks merged
    assert "ADB" in to_markdown(r2)


def test_safe_filename():
    assert safe_filename("Asian Development Bank / Pacific") == "asian_development_bank_pacific"
    assert safe_filename("???") == "report"


def test_missing_key_is_auth_error():
    with pytest.raises(AuthError):
        GeminiClient("", ["m"])


def test_client_reports_all_failures(monkeypatch):
    c = GeminiClient("k", ["m1", "m2"], retries=0)
    monkeypatch.setattr(c, "_call", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(LLMError, match="m1.*boom.*m2.*boom"):
        c.generate("p", Synthesis)
