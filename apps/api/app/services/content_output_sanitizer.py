from __future__ import annotations

import re


class ContentOutputSanitizer:
    """Removes model commentary, RAG leakage and unsupported promotional claims."""

    META_LINE_PATTERNS = (
        r"^essa resposta (?:segue|foi|está).*$",
        r"^esta resposta (?:segue|foi|está).*$",
        r"^este roteiro foi (?:criado|projetado).*$",
        r"^conteúdo (?:criado|gerado) com base.*$",
        r"^com base nos (?:materiais|documentos|dados).*$",
        r"^a resposta deve.*$",
    )

    UNSUPPORTED_PROMOTIONAL_PATTERNS = (
        r"\bconheça nossos? guard-rails\b",
        r"\buse nossos? guard-rails\b",
        r"\bcontrate nossos? serviços\b",
        r"\bfale com nossa equipe\b",
    )

    @classmethod
    def sanitize(cls, content: str) -> str:
        cleaned = re.sub(r"\[fonte\s+\d+\]", "", content, flags=re.IGNORECASE)
        cleaned = re.sub(r"@youraccount\b", "", cleaned, flags=re.IGNORECASE)

        lines: list[str] = []
        for raw_line in cleaned.splitlines():
            stripped = raw_line.strip()
            normalized = " ".join(stripped.lower().split())
            if stripped and any(
                re.match(pattern, normalized, flags=re.IGNORECASE)
                for pattern in cls.META_LINE_PATTERNS
            ):
                continue
            lines.append(raw_line.rstrip())

        cleaned = "\n".join(lines)
        for pattern in cls.UNSUPPORTED_PROMOTIONAL_PATTERNS:
            cleaned = re.sub(
                pattern,
                "saiba como implementar guard-rails",
                cleaned,
                flags=re.IGNORECASE,
            )

        cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()
