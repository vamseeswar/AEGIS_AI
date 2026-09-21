"""AEGIS AI — Multi-Format Document Parsing Engine
Extracts textual content and preserves page/section boundaries for PDF, DOCX, TXT, CSV, and JSON.
Includes smart whitespace normalization for PDFs with compressed text streams.
"""

import csv
import io
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from docx import Document as DocxDocument
from pypdf import PdfReader


@dataclass
class ParsedPage:
    """Represents an extracted unit of text with page number mapping."""
    page_number: int | None
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _normalize_pdf_text(text: str) -> str:
    """Normalizes PDF-extracted text that often lacks spaces between words.
    
    Many PDFs (especially resumes) produce text like 'PythonFastAPIRESTAPIs'
    because glyph spacing is encoded visually rather than as space characters.
    This function applies heuristics to restore readability.
    """
    if not text:
        return text

    # 1. Normalize unicode dashes, bullets, and special chars
    text = text.replace("\u2022", "• ").replace("\u2013", "–").replace("\u2014", "—")
    text = text.replace("\u00a0", " ")  # Non-breaking space → regular space

    # 2. Fix missing space between sentences (lowercase then uppercase)
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)

    # 3. Fix missing space after punctuation (period, comma, colon) before a word
    text = re.sub(r'([.,;:!?])([A-Za-z0-9])', r'\1 \2', text)

    # 4. Fix missing space between digit and letter transitions
    text = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)
    text = re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)

    # 5. Collapse multiple blank lines to double newline (paragraph boundary)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 6. Collapse multiple spaces into one
    text = re.sub(r'[ \t]{2,}', ' ', text)

    # 7. Fix common resume patterns: "EmailPhone" → "Email Phone"
    # Detect common email patterns and add spaces around them
    text = re.sub(r'(\S)(@\S+\.\S+)', r'\1 \2', text)
    text = re.sub(r'(\S)(https?://)', r'\1 \2', text)
    text = re.sub(r'(\S)(www\.)', r'\1 \2', text)

    return text.strip()


class BaseDocumentParser(ABC):
    """Abstract document parser."""

    @abstractmethod
    def parse(self, content: bytes, original_filename: str) -> list[ParsedPage]:
        """Parses raw file bytes into a sequence of ParsedPage objects."""
        pass


class PDFParser(BaseDocumentParser):
    """Extracts text from PDF documents preserving page numbers with smart normalization."""

    def parse(self, content: bytes, original_filename: str) -> list[ParsedPage]:
        stream = io.BytesIO(content)
        reader = PdfReader(stream)
        pages: list[ParsedPage] = []

        for idx, page in enumerate(reader.pages, start=1):
            raw_text = page.extract_text() or ""
            
            # Try extracting with layout mode for better spacing
            try:
                layout_text = page.extract_text(extraction_mode="layout") or ""
                # Use layout text if it has more spaces (better quality)
                if layout_text.count(" ") > raw_text.count(" "):
                    raw_text = layout_text
            except Exception:
                pass

            text = _normalize_pdf_text(raw_text.strip())
            if text:
                pages.append(
                    ParsedPage(
                        page_number=idx,
                        text=text,
                        metadata={"total_pages": len(reader.pages)},
                    )
                )

        if not pages:
            pages.append(
                ParsedPage(
                    page_number=1,
                    text=f"[Scanned or empty PDF: {original_filename}]",
                    metadata={"scanned": True},
                )
            )

        return pages


class DocxParser(BaseDocumentParser):
    """Extracts paragraphs and tables from DOCX documents."""

    def parse(self, content: bytes, original_filename: str) -> list[ParsedPage]:
        stream = io.BytesIO(content)
        doc = DocxDocument(stream)
        lines: list[str] = []

        for para in doc.paragraphs:
            clean_para = para.text.strip()
            if clean_para:
                lines.append(clean_para)

        for table in doc.tables:
            table_rows = []
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells]
                if any(row_cells):
                    table_rows.append(" | ".join(row_cells))
            if table_rows:
                lines.append("\n".join(table_rows))

        full_text = "\n\n".join(lines).strip()
        if not full_text:
            full_text = f"[Empty DOCX: {original_filename}]"

        return [ParsedPage(page_number=1, text=full_text, metadata={"type": "docx"})]


class TextParser(BaseDocumentParser):
    """Parses plain text files."""

    def parse(self, content: bytes, original_filename: str) -> list[ParsedPage]:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="replace")

        clean_text = text.strip()
        if not clean_text:
            clean_text = f"[Empty TXT: {original_filename}]"

        return [ParsedPage(page_number=1, text=clean_text, metadata={"type": "txt"})]


class CSVParser(BaseDocumentParser):
    """Extracts rows and tabular headers from CSV datasets."""

    def parse(self, content: bytes, original_filename: str) -> list[ParsedPage]:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="replace")

        reader = csv.reader(io.StringIO(text))
        rows = list(reader)

        if not rows:
            return [ParsedPage(page_number=1, text=f"[Empty CSV: {original_filename}]")]

        header = rows[0]
        formatted_rows = [f"Header: {', '.join(header)}"]

        for idx, row in enumerate(rows[1:], start=1):
            formatted_row = f"Row {idx}: " + ", ".join(
                f"{col}={val}" for col, val in zip(header, row, strict=False) if val.strip()
            )
            formatted_rows.append(formatted_row)

        full_text = "\n".join(formatted_rows)
        return [
            ParsedPage(
                page_number=1,
                text=full_text,
                metadata={"total_rows": len(rows), "columns": header},
            )
        ]


class JSONParser(BaseDocumentParser):
    """Parses JSON data structures into human-readable formatted representations."""

    def parse(self, content: bytes, original_filename: str) -> list[ParsedPage]:
        try:
            data = json.loads(content.decode("utf-8"))
            formatted = json.dumps(data, indent=2)
        except Exception:
            formatted = content.decode("utf-8", errors="replace")

        return [ParsedPage(page_number=1, text=formatted, metadata={"type": "json"})]


def get_document_parser(file_type: str) -> BaseDocumentParser:
    """Factory returning the parser matching the specified file type."""
    parsers: dict[str, BaseDocumentParser] = {
        "PDF": PDFParser(),
        "DOCX": DocxParser(),
        "TXT": TextParser(),
        "CSV": CSVParser(),
        "JSON": JSONParser(),
    }
    normalized_type = file_type.upper().strip()
    return parsers.get(normalized_type, TextParser())


def parse_document(file_bytes: bytes, file_type: str, original_filename: str = "doc") -> list[ParsedPage]:
    """Convenience function to parse file bytes according to file type."""
    parser = get_document_parser(file_type)
    return parser.parse(file_bytes, original_filename)
