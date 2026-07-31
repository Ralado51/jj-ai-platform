from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ContentValidationResult:
    is_valid: bool
    issues: tuple[str, ...]


class ContentOutputValidator:
    """Validates generated social content before it is returned to the client."""

    REQUIRED_SECTIONS = (
        "ideia central",
        "gancho",
        "roteiro",
        "título",
        "legenda",
        "hashtag",
        "chamada para ação",
    )

    PLACEHOLDER_PATTERNS = (
        r"\[insira[^\]]*\]",
        r"\[adicione[^\]]*\]",
        r"<insira[^>]*>",
        r"seu link aqui",
        r"@youraccount\b",
    )

    OUTLINE_PATTERNS = (
        r"\bcomeçar com\b",
        r"\bcomece com\b",
        r"\bexplicar o conceito\b",
        r"\bapresentar um exemplo\b",
        r"\bconcluir com\b",
        r"\bfalar sobre\b",
        r"\bmostrar como\b",
        r"\banimação rápida\b",
        r"\bfinalize com\b",
    )

    META_PATTERNS = (
        r"\bessa resposta segue\b",
        r"\besta resposta segue\b",
        r"\beste roteiro foi (?:criado|projetado)\b",
        r"\bcom base nos (?:materiais|documentos|dados)\b",
        r"\bmantendo o conteúdo baseado\b",
    )

    UNSUPPORTED_PROMOTIONAL_PATTERNS = (
        r"\bconheça nossos? guard-rails\b",
        r"\buse nossos? guard-rails\b",
        r"\bcontrate nossos? serviços\b",
        r"\bfale com nossa equipe\b",
    )

    def validate(self, content: str) -> ContentValidationResult:
        normalized = " ".join(content.lower().split())
        issues: list[str] = []

        if not content.strip():
            return ContentValidationResult(
                is_valid=False,
                issues=("A resposta está vazia.",),
            )

        for section in self.REQUIRED_SECTIONS:
            if section not in normalized:
                issues.append(f"Seção obrigatória ausente: {section}.")

        if len(re.findall(r"(?:opção|gancho)\s*\d", normalized)) < 3:
            issues.append("A resposta deve conter três opções de gancho completas.")

        if not re.search(r"\b\d{1,2}\s*[–-]\s*\d{1,2}\s*s\b|\b\d{1,2}\s*segundos?\b", normalized):
            issues.append("O roteiro deve conter marcação de tempo coerente.")

        if any(re.search(pattern, normalized) for pattern in self.OUTLINE_PATTERNS):
            issues.append(
                "O roteiro contém instruções ou tópicos em vez de falas completas prontas para gravação."
            )

        if "exemplo" not in normalized and "por exemplo" not in normalized:
            issues.append("O roteiro deve incluir ao menos um exemplo concreto.")

        if any(re.search(pattern, normalized) for pattern in self.PLACEHOLDER_PATTERNS):
            issues.append("A resposta contém placeholders que devem ser removidos.")

        if re.search(r"\[fonte\s+\d+\]", normalized):
            issues.append("A resposta contém citações indevidas para conteúdo criativo.")

        if any(re.search(pattern, normalized) for pattern in self.META_PATTERNS):
            issues.append("A resposta contém comentários do modelo sobre o próprio processo.")

        if any(
            re.search(pattern, normalized)
            for pattern in self.UNSUPPORTED_PROMOTIONAL_PATTERNS
        ):
            issues.append(
                "A resposta inventa um produto, serviço ou oferta comercial não informado no briefing."
            )

        hooks = self._extract_numbered_items(content, "gancho")
        titles = self._extract_numbered_items(content, "título")
        if len(hooks) >= 3 and len(titles) >= 3:
            normalized_hooks = {self._normalize_item(item) for item in hooks[:3]}
            normalized_titles = {self._normalize_item(item) for item in titles[:3]}
            if normalized_hooks == normalized_titles or len(
                normalized_hooks & normalized_titles
            ) >= 2:
                issues.append(
                    "Os títulos não devem repetir os ganchos; explore ângulos diferentes."
                )

        cta_index = normalized.rfind("chamada para ação")
        if cta_index >= 0 and cta_index < len(normalized) * 0.55:
            issues.append("A chamada para ação deve aparecer apenas no encerramento.")

        return ContentValidationResult(
            is_valid=not issues,
            issues=tuple(dict.fromkeys(issues)),
        )

    @staticmethod
    def _extract_numbered_items(content: str, label: str) -> list[str]:
        pattern = rf"(?:\*\*)?{label}\s*\d(?:\*\*)?\s*[:.-]\s*[\"“]?([^\n\"”]+)"
        return re.findall(pattern, content, flags=re.IGNORECASE)

    @staticmethod
    def _normalize_item(value: str) -> str:
        return re.sub(r"[^a-z0-9áàâãéêíóôõúç]+", " ", value.lower()).strip()

    @staticmethod
    def build_refinement_instructions(result: ContentValidationResult) -> str:
        if result.is_valid:
            return ""

        issue_lines = "\n".join(f"- {issue}" for issue in result.issues)
        return (
            "Reescreva a resposta preservando o briefing e corrigindo apenas os problemas abaixo:\n"
            f"{issue_lines}\n\n"
            "Entregue conteúdo final pronto para publicação, sem comentar o processo de revisão."
        )
