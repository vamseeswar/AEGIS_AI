"""AEGIS AI — Recursive Character Text Chunker
Splits textual content across natural semantic boundaries (paragraphs, sentences, words)
while preserving exact page number metadata and configuring chunk size & overlap.
"""

from dataclasses import dataclass
from typing import Any

from backend.rag.parsers import ParsedPage


@dataclass
class TextChunk:
    chunk_index: int
    page_number: int | None
    content: str
    metadata: dict[str, Any]


class RecursiveCharacterChunker:
    """Recursively splits text using a hierarchy of separators while preserving page boundaries."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: list[str] | None = None,
    ):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size.")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", "? ", "! ", "; ", " ", ""]

    def _split_text(self, text: str, separators: list[str]) -> list[str]:
        """Recursively splits text until chunks fit within chunk_size."""
        final_chunks: list[str] = []
        separator = separators[-1]
        new_separators: list[str] = []

        for i, sep in enumerate(separators):
            if sep == "":
                separator = ""
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1 :]
                break

        splits = text.split(separator) if separator else list(text)

        good_splits: list[str] = []
        for s in splits:
            if not s.strip():
                continue
            if len(s) < self.chunk_size:
                good_splits.append(s)
            else:
                if good_splits:
                    merged = self._merge_splits(good_splits, separator)
                    final_chunks.extend(merged)
                    good_splits = []
                if new_separators:
                    sub_chunks = self._split_text(s, new_separators)
                    final_chunks.extend(sub_chunks)
                else:
                    # Character slice fallback
                    for idx in range(0, len(s), self.chunk_size - self.chunk_overlap):
                        final_chunks.append(s[idx : idx + self.chunk_size])

        if good_splits:
            merged = self._merge_splits(good_splits, separator)
            final_chunks.extend(merged)

        return final_chunks

    def _merge_splits(self, splits: list[str], separator: str) -> list[str]:
        """Merges small text fragments up to chunk_size with sliding window overlap."""
        docs: list[str] = []
        current_doc: list[str] = []
        total = 0

        for d in splits:
            _len = len(d)
            if total + _len + (len(separator) if current_doc else 0) > self.chunk_size:
                if total > 0:
                    doc = separator.join(current_doc).strip()
                    if doc:
                        docs.append(doc)
                    # Keep elements within overlap window
                    while total > self.chunk_overlap and current_doc:
                        popped = current_doc.pop(0)
                        total -= len(popped) + len(separator)
            current_doc.append(d)
            total += _len + (len(separator) if len(current_doc) > 1 else 0)

        doc = separator.join(current_doc).strip()
        if doc:
            docs.append(doc)

        return docs

    def chunk_pages(self, pages: list[ParsedPage]) -> list[TextChunk]:
        """Chunks a list of ParsedPage objects preserving page numbers."""
        chunks: list[TextChunk] = []
        chunk_counter = 0

        for page in pages:
            raw_text = page.text.strip()
            if not raw_text:
                continue

            page_splits = self._split_text(raw_text, self.separators)

            for split in page_splits:
                cleaned = split.strip()
                if not cleaned:
                    continue

                chunk_metadata = dict(page.metadata)
                chunk_metadata["char_count"] = len(cleaned)

                chunks.append(
                    TextChunk(
                        chunk_index=chunk_counter,
                        page_number=page.page_number,
                        content=cleaned,
                        metadata=chunk_metadata,
                    )
                )
                chunk_counter += 1

        return chunks
