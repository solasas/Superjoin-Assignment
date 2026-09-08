"""PDF -> pages -> chunks. Nothing here knows anything about what kind of
document it's looking at; it just extracts text and groups it into
LLM-sized windows, keeping track of exactly which page(s) each chunk (and
later each fact) came from so every fact can be traced back to evidence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import pdfplumber

from . import config


@dataclass
class Page:
    number: int  # 1-indexed, matches how a human would cite the page
    text: str


@dataclass
class Chunk:
    index: int
    page_start: int
    page_end: int
    text: str
    relevance_score: float = None
    kept: bool = True


def extract_pages(pdf_path: str, only_pages: set[int] | None = None) -> list[Page]:
    """Extract page text. If `only_pages` is given, every other page is
    still counted (so page numbers stay faithful to the original PDF for
    evidence citations) but its text is left empty and it will be dropped
    by the relevance filter. This is what lets you scope ingestion of a
    very large PDF to specific pages you already know matter, without
    losing the true page numbering that grounding depends on.
    """
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            if only_pages is not None and i not in only_pages:
                pages.append(Page(number=i, text=""))
                continue
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            pages.append(Page(number=i, text=text))
    return pages


def _normalize_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def group_pages_into_chunks(
    pages: list[Page],
    pages_per_chunk: int = None,
    max_chars: int = None,
) -> list[Chunk]:
    """Merge consecutive pages into chunks of roughly `max_chars`, so a
    single LLM call sees a coherent window of text with clear page
    boundaries rather than one call per page (too many calls) or the whole
    document at once (too big, and loses per-page grounding).
    """
    pages_per_chunk = pages_per_chunk or config.PAGES_PER_CHUNK
    max_chars = max_chars or config.MAX_CHUNK_CHARS

    chunks: list[Chunk] = []
    buf_pages: list[Page] = []
    buf_len = 0

    def flush():
        nonlocal buf_pages, buf_len
        if not buf_pages:
            return
        text = "\n\n".join(f"[page {p.number}]\n{_normalize_whitespace(p.text)}" for p in buf_pages if p.text.strip())
        if text.strip():
            chunks.append(
                Chunk(
                    index=len(chunks),
                    page_start=buf_pages[0].number,
                    page_end=buf_pages[-1].number,
                    text=text,
                )
            )
        buf_pages = []
        buf_len = 0

    for page in pages:
        if not page.text.strip():
            continue  # blank, or deliberately skipped via only_pages
        page_len = len(page.text)
        would_exceed_chars = buf_len + page_len > max_chars and buf_pages
        would_exceed_count = len(buf_pages) >= pages_per_chunk
        if would_exceed_chars or would_exceed_count:
            flush()
        buf_pages.append(page)
        buf_len += page_len

    flush()
    return chunks
