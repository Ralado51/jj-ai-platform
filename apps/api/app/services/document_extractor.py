from __future__ import annotations

import csv
import json
from io import BytesIO, StringIO

from docx import Document as DocxDocument
from pypdf import PdfReader


class DocumentExtractionError(RuntimeError):
    """Raised when text cannot be extracted from a supported document."""


SUPPORTED_EXTRACTION_MIME_TYPES = {
    "application/json",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/csv",
    "text/markdown",
    "text/plain",
}


class DocumentExtractor:
    def extract(self, *, content: bytes, mime_type: str) -> str:
        try:
            if mime_type == "application/pdf":
                return self._extract_pdf(content)
            if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                return self._extract_docx(content)
            if mime_type == "application/json":
                return self._extract_json(content)
            if mime_type == "text/csv":
                return self._extract_csv(content)
            if mime_type in {"text/plain", "text/markdown"}:
                return self._decode_text(content)
        except (ValueError, UnicodeDecodeError, OSError) as exc:
            raise DocumentExtractionError("Unable to extract document text.") from exc

        raise DocumentExtractionError(f"Unsupported extraction MIME type: {mime_type}")

    @staticmethod
    def _extract_pdf(content: bytes) -> str:
        reader = PdfReader(BytesIO(content))
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
        return "\n\n".join(page for page in pages if page)

    @staticmethod
    def _extract_docx(content: bytes) -> str:
        document = DocxDocument(BytesIO(content))
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs]
        return "\n".join(paragraph for paragraph in paragraphs if paragraph)

    @classmethod
    def _extract_json(cls, content: bytes) -> str:
        value = json.loads(cls._decode_text(content))
        return json.dumps(value, ensure_ascii=False, indent=2)

    @classmethod
    def _extract_csv(cls, content: bytes) -> str:
        source = StringIO(cls._decode_text(content))
        rows = csv.reader(source)
        return "\n".join(" | ".join(cell.strip() for cell in row) for row in rows)

    @staticmethod
    def _decode_text(content: bytes) -> str:
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise UnicodeDecodeError("utf-8", content, 0, 1, "Unsupported text encoding")
