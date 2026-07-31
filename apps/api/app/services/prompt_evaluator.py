from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PromptEvaluationScores:
    hook: float
    storytelling: float
    clarity: float
    originality: float
    call_to_action: float
    structure: float

    @property
    def overall(self) -> float:
        values = (
            self.hook,
            self.storytelling,
            self.clarity,
            self.originality,
            self.call_to_action,
            self.structure,
        )
        return round(sum(values) / len(values), 2)


@dataclass(frozen=True)
class PromptEvaluationResult:
    scores: PromptEvaluationScores
    issues: tuple[str, ...]
    strengths: tuple[str, ...]
    passed: bool


class PromptEvaluator:
    """Scores generated content with deterministic, explainable heuristics."""

    def __init__(self, *, minimum_score: float = 8.0) -> None:
        if minimum_score < 0 or minimum_score > 10:
            raise ValueError("minimum_score must be between 0 and 10")
        self.minimum_score = minimum_score

    def evaluate(self, content: str) -> PromptEvaluationResult:
        normalized = " ".join(content.lower().split())
        issues: list[str] = []
        strengths: list[str] = []

        if not content.strip():
            scores = PromptEvaluationScores(0, 0, 0, 0, 0, 0)
            return PromptEvaluationResult(
                scores=scores,
                issues=("A resposta está vazia.",),
                strengths=(),
                passed=False,
            )

        hook_score = self._score_hooks(normalized, issues, strengths)
        storytelling_score = self._score_storytelling(normalized, issues, strengths)
        clarity_score = self._score_clarity(content, normalized, issues, strengths)
        originality_score = self._score_originality(content, normalized, issues, strengths)
        cta_score = self._score_cta(normalized, issues, strengths)
        structure_score = self._score_structure(normalized, issues, strengths)

        scores = PromptEvaluationScores(
            hook=hook_score,
            storytelling=storytelling_score,
            clarity=clarity_score,
            originality=originality_score,
            call_to_action=cta_score,
            structure=structure_score,
        )

        return PromptEvaluationResult(
            scores=scores,
            issues=tuple(dict.fromkeys(issues)),
            strengths=tuple(dict.fromkeys(strengths)),
            passed=scores.overall >= self.minimum_score,
        )

    @staticmethod
    def _score_hooks(normalized: str, issues: list[str], strengths: list[str]) -> float:
        hooks = re.findall(r"(?:gancho|opção)\s*\d\s*[:.-]\s*([^\n]+)", normalized)
        score = 4.0
        if len(hooks) >= 3:
            score += 3.0
            strengths.append("A resposta oferece pelo menos três opções de gancho.")
        else:
            issues.append("Forneça três ganchos completos e distintos.")

        hook_text = " ".join(hooks)
        if any(token in hook_text for token in ("?", "como ", "por que", "segredo", "erro")):
            score += 2.0
        else:
            issues.append("Os ganchos precisam gerar curiosidade ou tensão imediatamente.")

        if hooks and len(set(hooks)) == len(hooks):
            score += 1.0
        return min(score, 10.0)

    @staticmethod
    def _score_storytelling(normalized: str, issues: list[str], strengths: list[str]) -> float:
        score = 3.0
        progression_markers = ("problema", "consequência", "solução", "resultado", "por isso")
        marker_count = sum(marker in normalized for marker in progression_markers)
        if marker_count >= 2:
            score += 3.0
            strengths.append("O conteúdo apresenta progressão narrativa.")
        else:
            issues.append("Adicione uma progressão clara de problema, consequência e solução.")

        if re.search(r"\b\d{1,2}\s*[–-]\s*\d{1,2}\s*s\b", normalized):
            score += 2.0
        else:
            issues.append("Inclua marcações de tempo no roteiro.")

        if "exemplo" in normalized or "por exemplo" in normalized:
            score += 2.0
            strengths.append("O roteiro inclui um exemplo concreto.")
        else:
            issues.append("Inclua ao menos um exemplo concreto.")
        return min(score, 10.0)

    @staticmethod
    def _score_clarity(content: str, normalized: str, issues: list[str], strengths: list[str]) -> float:
        words = re.findall(r"\w+", content, flags=re.UNICODE)
        score = 6.0
        if 80 <= len(words) <= 700:
            score += 2.0
            strengths.append("A resposta tem extensão adequada para leitura e uso.")
        elif len(words) < 80:
            issues.append("A resposta está curta demais para entregar conteúdo completo.")
        else:
            issues.append("A resposta está excessivamente longa para o formato solicitado.")

        if not re.search(r"\[(?:fonte|insira|adicione)[^\]]*\]", normalized):
            score += 1.0
        else:
            issues.append("Remova citações e placeholders do conteúdo final.")

        if not re.search(r"\b(?:começar com|explicar o conceito|apresentar um exemplo|concluir com)\b", normalized):
            score += 1.0
        else:
            issues.append("Troque instruções de produção por falas prontas para gravação.")
        return min(score, 10.0)

    @staticmethod
    def _score_originality(content: str, normalized: str, issues: list[str], strengths: list[str]) -> float:
        score = 5.0
        quoted_lines = [
            re.sub(r"\s+", " ", line.strip().lower())
            for line in content.splitlines()
            if len(line.strip()) >= 20
        ]
        if quoted_lines:
            unique_ratio = len(set(quoted_lines)) / len(quoted_lines)
            if unique_ratio >= 0.85:
                score += 3.0
                strengths.append("As seções apresentam boa diversidade textual.")
            elif unique_ratio < 0.65:
                issues.append("As versões repetem frases demais; explore ângulos distintos.")

        titles = re.findall(r"título\s*\d\s*[:.-]\s*([^\n]+)", normalized)
        if len(set(titles)) >= 3:
            score += 2.0
        else:
            issues.append("Os títulos precisam explorar ângulos diferentes.")
        return min(score, 10.0)

    @staticmethod
    def _score_cta(normalized: str, issues: list[str], strengths: list[str]) -> float:
        score = 4.0
        cta_index = normalized.rfind("chamada para ação")
        if cta_index >= 0:
            score += 3.0
            strengths.append("A resposta inclui chamada para ação.")
            if cta_index >= len(normalized) * 0.65:
                score += 2.0
            else:
                issues.append("Posicione a CTA somente no encerramento.")
        else:
            issues.append("Inclua uma chamada para ação final.")

        if any(term in normalized for term in ("comente", "compartilhe", "salve", "siga", "inscreva")):
            score += 1.0
        return min(score, 10.0)

    @staticmethod
    def _score_structure(normalized: str, issues: list[str], strengths: list[str]) -> float:
        sections = (
            "ideia central",
            "gancho",
            "roteiro",
            "título",
            "legenda",
            "hashtag",
            "chamada para ação",
        )
        found = sum(section in normalized for section in sections)
        score = round((found / len(sections)) * 10, 2)
        if found == len(sections):
            strengths.append("Todas as seções obrigatórias estão presentes.")
        else:
            issues.append("Complete todas as sete seções obrigatórias.")
        return score
