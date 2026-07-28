from __future__ import annotations

import re


class TextChunker:
    def __init__(self, *, chunk_size: int = 3200, overlap: int = 600) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be non-negative and smaller than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, text: str) -> list[str]:
        normalized = re.sub(r"\r\n?", "\n", text).strip()
        if not normalized:
            return []

        chunks: list[str] = []
        start = 0
        length = len(normalized)

        while start < length:
            target_end = min(start + self.chunk_size, length)
            end = self._find_boundary(normalized, start, target_end)
            chunk = normalized[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= length:
                break
            start = max(end - self.overlap, start + 1)

        return chunks

    @staticmethod
    def _find_boundary(text: str, start: int, target_end: int) -> int:
        if target_end >= len(text):
            return len(text)

        search_start = start + max((target_end - start) // 2, 1)
        for separator in ("\n\n", "\n", ". ", " "):
            position = text.rfind(separator, search_start, target_end)
            if position != -1:
                return position + len(separator)
        return target_end
