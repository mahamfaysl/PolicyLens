"""PDF text extraction and page-aware chunking."""
import io
import re
from dataclasses import dataclass
from typing import BinaryIO, List, Union

from pypdf import PdfReader


class DocumentError(ValueError):
    """The document cannot be analysed (unreadable, encrypted, or no text layer)."""


@dataclass
class ParsedDocument:
    pages: List[str]  # pages[0] is page 1

    @property
    def characters(self) -> int:
        return sum(len(p) for p in self.pages)

    def render(self, start: int = 1, end: int = None) -> str:
        end = end or len(self.pages)
        return "\n".join(_page_block(n, self.pages[n - 1]) for n in range(start, end + 1) if self.pages[n - 1])


def _page_block(number: int, text: str) -> str:
    return f"--- PAGE {number} ---\n{text}"


def _clean(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def read_pdf(source: Union[bytes, BinaryIO], max_pages: int = 2000) -> ParsedDocument:
    stream = io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else source
    try:
        reader = PdfReader(stream)
        if reader.is_encrypted and not reader.decrypt(""):
            raise DocumentError("The PDF is password-protected.")
        total = len(reader.pages)
    except DocumentError:
        raise
    except Exception as e:
        raise DocumentError(f"Could not open the PDF: {e}") from e

    if total > max_pages:
        raise DocumentError(f"The PDF has {total} pages; the limit is {max_pages}.")

    pages = []
    for page in reader.pages:
        try:
            pages.append(_clean(page.extract_text() or ""))
        except Exception:
            pages.append("")  # one unreadable page should not sink the whole document

    doc = ParsedDocument(pages)
    if doc.characters < 100:
        raise DocumentError(
            "No extractable text found. The PDF looks scanned (image-only); run OCR on it first."
        )
    return doc


def chunk_document(doc: ParsedDocument, max_chars: int) -> List[str]:
    """Group whole pages into chunks of about max_chars; oversized pages are split."""
    chunks: List[str] = []
    current: List[str] = []
    size = 0

    def flush():
        nonlocal current, size
        if current:
            chunks.append("\n".join(current))
        current, size = [], 0

    for number, text in enumerate(doc.pages, 1):
        if not text:
            continue
        parts = [text[i : i + max_chars] for i in range(0, len(text), max_chars)]
        for part in parts:
            block = _page_block(number, part)
            if size and size + len(block) > max_chars:
                flush()
            current.append(block)
            size += len(block)
    flush()
    return chunks
